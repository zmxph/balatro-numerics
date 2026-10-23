-- Lovely appends this file after Balatro's main.lua. Keep all locals scoped.
do
    if not HAND_PROBABILITIES then
        local factory = require('hprob_engine')
        local joker_factory = require('hprob_jokers')
        local joint_factory = require('hprob_joint_suits')
        local joker_model = joker_factory()
        local H = {version = '1.4.1', display = {}, result = nil, marginal = nil, tooltip_tick = 0,
            status = 'idle', elapsed = 0, rows_active = false}
        HAND_PROBABILITIES = H
        local names = {
            ['Flush Five'] = 'flush_five', ['Flush House'] = 'flush_house',
            ['Five of a Kind'] = 'five', ['Straight Flush'] = 'straight_flush',
            ['Four of a Kind'] = 'four', ['Full House'] = 'full_house',
            ['Flush'] = 'flush', ['Straight'] = 'straight', ['Three of a Kind'] = 'three',
            ['Two Pair'] = 'two_pair', ['Pair'] = 'pair', ['High Card'] = 'high_card',
        }
        local suits = {Spades = 1, Hearts = 2, Clubs = 3, Diamonds = 4}
        local function chinese()
            local lang = G and G.SETTINGS and G.SETTINGS.language or 'en-us'
            return lang == 'zh_CN' or lang == 'zh_TW'
        end
        local function tr(cn, en) return chinese() and cn or en end
        local function active()
            return G and G.STAGES and G.STAGE == G.STAGES.RUN and G.GAME and
                G.hand and G.hand.config and G.playing_cards
        end
        local function format_probability(p)
            if p == 0 then return '0%' end
            if p == 1 then return '100%' end
            if p < 0.0001 then return '<0.01%' end
            if p > 0.9999 then return '>99.99%' end
            return string.format('%.2f%%', p * 100)
        end
        H.format_probability = format_probability
        local function pending(value)
            for name in pairs(names) do H.display[name] = value end
        end
        pending('...')
        -- Full current deck, including hand/discard/play. Never use only G.deck.cards.
        -- Read base.id directly: Card:get_id() can consume game RNG for stone cards.
        local function snapshot()
            if not active() then return end
            local M, unusual = {}, false
            for s = 1, 4 do M[s] = {}; for r = 1, 13 do M[s][r] = 0 end end
            for _, card in ipairs(G.playing_cards) do
                local s = card.base and suits[card.base.suit]
                local id = card.base and card.base.id
                if not s or type(id) ~= 'number' or id < 2 or id > 14 or id % 1 ~= 0 then
                    return {unsupported = true, key = 'unsupported'}
                end
                local r = id == 14 and 1 or id
                M[s][r] = M[s][r] + 1
                local a = card.ability or {}
                if a.effect == 'Stone Card' or a.name == 'Wild Card' then unusual = true end
            end
            for _, joker in ipairs(G.jokers and G.jokers.cards or {}) do
                local name = joker.ability and joker.ability.name
                if name == 'Four Fingers' or name == 'Shortcut' or name == 'Smeared Joker' then unusual = true end
            end
            local m = math.max(0, tonumber(G.hand.config.card_limit) or 0)
            local k = math.min(#G.playing_cards, math.ceil(1.8 * m))
            local key = {tostring(m), tostring(k)}
            for s = 1, 4 do for r = 1, 13 do key[#key + 1] = tostring(M[s][r]) end end
            local joker_context, joker_signature = joker_model.context(G)
            key[#key + 1] = joker_signature
            return {matrix = M, m = m, k = k, n = #G.playing_cards,
                key = table.concat(key, ':'), unusual = unusual, joker_context = joker_context}
        end
        H.snapshot = snapshot
        local worker_code = [[
            local bytecode, input, output, joker_bytecode, joint_bytecode = ...
            local ok, err = pcall(function()
                local engine = assert(loadstring(bytecode))()
                local jokers = assert(loadstring(joker_bytecode))()
                local joint = assert(loadstring(joint_bytecode))()
                local result = engine.compute(input.matrix, input.k, function(marginal, n, k)
                    output:push({phase = 'marginal', key = input.key, marginal = marginal, n = n, k = k})
                end, jokers.queries(input.matrix, input.joker_context))
                jokers.evaluate(result, joint.compute(input.matrix, input.k), input.joker_context)
                result.m = input.m
                output:push({phase = 'complete', key = input.key, result = result})
            end)
            if not ok then output:push({phase = 'error', key = input.key, error = tostring(err)}) end
        ]]
        local function apply_marginal(marginal)
            H.marginal = marginal
            for name, kind in pairs(names) do H.display[name] = format_probability(marginal[kind]) end
        end
        local function fail(err)
            H.status, H.error = 'error', tostring(err)
            H.result, H.marginal = nil, nil
            pending('--')
            print('[HandProbabilities] ' .. H.error)
        end
        local function launch(input)
            H.job_key, H.status, H.error = input.key, 'calculating', nil
            local ok, err = pcall(function()
                H.channel = love.thread.newChannel()
                H.thread = love.thread.newThread(worker_code)
                H.thread:start(string.dump(factory), input, H.channel, string.dump(joker_factory), string.dump(joint_factory))
            end)
            if not ok then H.thread, H.channel = nil, nil; fail(err) end
        end
        function H.refresh(force)
            if not active() then
                H.current, H.key, H.result, H.marginal = nil, nil, nil, nil
                H.status = 'idle'
                pending('...')
                return
            end
            if force then
                local input = snapshot()
                H.current = input
                if input.key ~= H.key then
                    H.key, H.result, H.marginal, H.error = input.key, nil, nil, nil
                    H.status = input.unsupported and 'unsupported' or 'pending'
                    pending(input.unsupported and '--' or '...')
                end
            end
            -- Capture stopped state before draining: a thread can push its final
            -- message between pop() and isRunning(). Never discard that message.
            local stopped = H.thread and not H.thread:isRunning()
            if H.channel then
                while true do
                    local msg = H.channel:pop()
                    if not msg then break end
                    if msg.key == H.key then
                        if msg.phase == 'marginal' then
                            apply_marginal(msg.marginal)
                            H.status = 'matrices'
                        elseif msg.phase == 'complete' then
                            H.result, H.status = msg.result, 'ready'
                            apply_marginal(msg.result.marginal)
                        else fail(msg.error) end
                    end
                end
            end
            if H.thread and stopped then
                local err = H.thread:getError()
                if err and H.job_key == H.key then fail(err) end
                H.thread, H.channel = nil, nil
            end
            if not H.thread and H.current and not H.current.unsupported and H.status == 'pending' then
                launch(H.current)
            end
        end
        local old_update = love.update
        love.update = function(dt, ...)
            if old_update then old_update(dt, ...) end
            H.elapsed = H.elapsed + dt
            local force = H.elapsed >= 0.5
            if force then H.elapsed = 0; H.tooltip_tick = H.tooltip_tick + 1 end
            H.refresh(force)
        end

        local function tooltip()
            local input = H.current or {}
            local text = {
                tr('当前完整牌组可组成该牌型的概率', 'Chance to form this hand from the full current deck'),
                tr('手牌上限 ', 'Hand limit ') .. tostring(input.m or '-') ..
                    tr('，计算抽牌 ', ', effective draw ') .. tostring(input.k or '-') ..
                    tr(' 张；牌组 ', '; deck ') .. tostring(input.n or '-'),
                tr('抽牌数 = 向上取整(1.8 × 手牌上限)，不超过牌组张数',
                    'Draw = ceil(1.8 x hand limit), capped at deck size'),
                tr('各牌型独立统计，可以重叠；不是最强牌型的概率',
                    'Overlapping formability events, not the best-hand distribution'),
                tr('基础规则模型：未计入四指、捷径、四色合一及特殊牌效果',
                    'Base rules: no Four Fingers, Shortcut, Smeared or special-card effects'),
            }
            if input.unusual then text[#text + 1] = tr('当前有特殊规则：这里显示基础模型参考值',
                'Special effects detected: these are base-model reference values') end
            if H.status == 'error' then text[#text + 1] = tr('计算失败，详细原因见 Lovely 日志', 'Calculation failed; see Lovely log') end
            if H.status == 'unsupported' then text[#text + 1] = tr('存在非标准点数或花色，暂不支持', 'Custom ranks or suits are not supported') end
            return {text = text}
        end
        local old_row = create_UIBox_current_hand_row
        create_UIBox_current_hand_row = function(handname, simple, ...)
            local row = old_row(handname, simple, ...)
            if not row or simple or not H.rows_active or not names[handname] then return row end
            -- Recover the space for the new column from the vanilla name column.
            local label = row.nodes and row.nodes[1]
            local name_column = label and label.nodes and label.nodes[2]
            if name_column and name_column.config and name_column.config.minw == 4.5 then
                name_column.config.minw, name_column.config.maxw = 3.35, 3.35
                if name_column.nodes and name_column.nodes[1] then name_column.nodes[1].config.scale = 0.41 end
            end
            row.nodes[#row.nodes + 1] = {n = G.UIT.C, config = {
                align = 'cm', padding = 0.04, r = 0.1, minw = 1.45,
                colour = G.C.L_BLACK, hover = true, on_demand_tooltip = tooltip(),
            }, nodes = {{n = G.UIT.T, config = {
                ref_table = H.display, ref_value = handname, scale = 0.34,
                colour = G.C.GREEN, shadow = true,
            }}}}
            return row
        end
        local old_hands = create_UIBox_current_hands
        create_UIBox_current_hands = function(simple, ...)
            local enabled = not simple and active()
            if enabled then H.refresh(true) end
            H.rows_active = enabled
            local ok, ui = pcall(old_hands, simple, ...)
            H.rows_active = false
            if not ok then error(ui) end
            if enabled and ui and ui.nodes then
                table.insert(ui.nodes, 1, {n = G.UIT.R, config = {align = 'cr', padding = 0.02}, nodes = {
                    {n = G.UIT.T, config = {text = tr('可组成概率（基础模型）', 'Formability (base rules)'),
                        scale = 0.28, colour = G.C.UI.TEXT_LIGHT}},
                }})
            end
            return ui
        end
        require('hprob_tooltip')(H, joker_model, names, active, tr)
    end
end
