-- Serializable evaluator. Catalog below is generated from joker_catalog.json.
return function()
    local specs = {{["key"]="j_greedy_joker",["category"]="suit",["query"]="diamonds",["mult"]=3,["mult_path"]="extra.s_mult"},
        {["key"]="j_lusty_joker",["category"]="suit",["query"]="hearts",["mult"]=3,["mult_path"]="extra.s_mult"},
        {["key"]="j_wrathful_joker",["category"]="suit",["query"]="spades",["mult"]=3,["mult_path"]="extra.s_mult"},
        {["key"]="j_gluttenous_joker",["category"]="suit",["query"]="clubs",["mult"]=3,["mult_path"]="extra.s_mult"},
        {["key"]="j_onyx_agate",["category"]="suit",["query"]="clubs",["mult"]=7,["mult_path"]="extra"},
        {["key"]="j_arrowhead",["category"]="suit",["query"]="spades",["chips"]=50,["chips_path"]="extra"},
        {["key"]="j_fibonacci",["category"]="rank_set",["query"]="fibonacci",["mult"]=8,["mult_path"]="extra"},
        {["key"]="j_even_steven",["category"]="rank_set",["query"]="even",["mult"]=4,["mult_path"]="extra"},
        {["key"]="j_odd_todd",["category"]="rank_set",["query"]="odd",["chips"]=31,["chips_path"]="extra"},
        {["key"]="j_scholar",["category"]="rank_set",["query"]="aces",["mult"]=4,["chips"]=20,["mult_path"]="extra.mult",["chips_path"]="extra.chips"},
        {["key"]="j_walkie_talkie",["category"]="rank_set",["query"]="walkie",["mult"]=4,["chips"]=10,["mult_path"]="extra.mult",["chips_path"]="extra.chips"},
        {["key"]="j_smiley",["category"]="rank_set",["query"]="faces",["mult"]=5,["mult_path"]="extra"},
        {["key"]="j_scary_face",["category"]="rank_set",["query"]="faces",["chips"]=30,["chips_path"]="extra"},
        {["key"]="j_bloodstone",["category"]="suit",["query"]="hearts",["x"]=1.5,["odds"]=2,["x_path"]="extra.Xmult",["odds_path"]="extra.odds"},
        {["key"]="j_ancient",["category"]="suit",["query"]="ancient",["x"]=1.5,["x_path"]="extra"},
        {["key"]="j_seeing_double",["category"]="multi_suit",["event"]="seeing_double",["x"]=2,["x_path"]="extra"},
        {["key"]="j_flower_pot",["category"]="multi_suit",["event"]="flower_pot",["x"]=3,["x_path"]="extra"},
        {["key"]="j_photograph",["category"]="rank_set",["query"]="faces",["x"]=2,["once"]=true,["x_path"]="extra"},
        {["key"]="j_idol",["category"]="cell",["query"]="idol",["x"]=2,["x_path"]="extra"},
        {["key"]="j_triboulet",["category"]="rank_set",["query"]="kings_queens",["x"]=2,["x_path"]="extra"},
        {["key"]="j_jolly",["category"]="hand_type",["trigger"]="pair",["mult"]=8,["mult_path"]="t_mult"},
        {["key"]="j_zany",["category"]="hand_type",["trigger"]="three",["mult"]=12,["mult_path"]="t_mult"},
        {["key"]="j_mad",["category"]="hand_type",["trigger"]="two_pair",["mult"]=10,["mult_path"]="t_mult"},
        {["key"]="j_crazy",["category"]="hand_type",["trigger"]="straight",["mult"]=12,["mult_path"]="t_mult"},
        {["key"]="j_droll",["category"]="hand_type",["trigger"]="flush",["mult"]=10,["mult_path"]="t_mult"},
        {["key"]="j_sly",["category"]="hand_type",["trigger"]="pair",["chips"]=50,["chips_path"]="t_chips"},
        {["key"]="j_wily",["category"]="hand_type",["trigger"]="three",["chips"]=100,["chips_path"]="t_chips"},
        {["key"]="j_clever",["category"]="hand_type",["trigger"]="two_pair",["chips"]=80,["chips_path"]="t_chips"},
        {["key"]="j_devious",["category"]="hand_type",["trigger"]="straight",["chips"]=100,["chips_path"]="t_chips"},
        {["key"]="j_crafty",["category"]="hand_type",["trigger"]="flush",["chips"]=80,["chips_path"]="t_chips"},
        {["key"]="j_duo",["category"]="hand_type",["trigger"]="pair",["x"]=2,["x_path"]="Xmult"},
        {["key"]="j_trio",["category"]="hand_type",["trigger"]="three",["x"]=3,["x_path"]="Xmult"},
        {["key"]="j_family",["category"]="hand_type",["trigger"]="four",["x"]=4,["x_path"]="Xmult"},
        {["key"]="j_order",["category"]="hand_type",["trigger"]="straight",["x"]=3,["x_path"]="Xmult"},
        {["key"]="j_tribe",["category"]="hand_type",["trigger"]="flush",["x"]=2,["x_path"]="Xmult"}} -- generated from joker_catalog.json
    local J = {catalog = specs}
    local kinds = {'pair','two_pair','three','four','five','full_house','flush','straight','straight_flush','flush_house','flush_five','high_card'}
    local suit_ids = {Spades=1, Hearts=2, Clubs=3, Diamonds=4}
    local sets = {fibonacci={1,2,3,5,8}, even={2,4,6,8,10}, odd={1,3,5,7,9},
        aces={1}, walkie={4,10}, faces={11,12,13}, kings_queens={12,13}}
    local suits = {spades=1, hearts=2, clubs=3, diamonds=4}
    local subtypes = {
        high_card={}, pair={pair=true}, two_pair={pair=true,two_pair=true}, three={pair=true,three=true},
        four={pair=true,three=true,four=true}, five={pair=true,three=true,four=true},
        full_house={pair=true,two_pair=true,three=true}, straight={straight=true}, flush={flush=true},
        straight_flush={straight=true,flush=true}, flush_house={pair=true,two_pair=true,three=true,flush=true},
        flush_five={pair=true,three=true,four=true,flush=true},
    }
    function J.queries(M, ctx)
        ctx = ctx or {}
        local filters = {}
        local function make(name, predicate)
            local target = {}
            for s = 1, 4 do
                target[s] = {}
                for r = 1, 13 do target[s][r] = predicate(s,r) and M[s][r] or 0 end
            end
            filters[name] = target
        end
        for name, list in pairs(sets) do
            local lookup = {}; for _, r in ipairs(list) do lookup[r] = true end
            make(name, function(_,r) return lookup[r] end)
        end
        for name, suit in pairs(suits) do make(name, function(s) return s == suit end) end
        if ctx.ancient_suit then make('ancient', function(s) return s == ctx.ancient_suit end) end
        if ctx.idol_suit and ctx.idol_rank then make('idol', function(s,r) return s == ctx.idol_suit and r == ctx.idol_rank end) end
        return filters
    end
    local function read_params(spec, cfg)
        local out = {}
        for _, name in ipairs({'mult','chips','x','odds'}) do
            local value = cfg
            local path = spec[name .. '_path']
            if path then
                for part in string.gmatch(path, '[^.]+') do value = type(value) == 'table' and value[part] or nil end
            else value = nil end
            if path == 'Xmult' and cfg and type(cfg.x_mult) == 'number' then value = cfg.x_mult end
            out[name] = type(value) == 'number' and value or spec[name] or 0
        end
        return out
    end
    function J.context(G)
        local round = G.GAME.current_round or {}
        local idol, ancient = round.idol_card or {}, round.ancient_card or {}
        local id = idol.id
        local ctx = {ancient_suit=suit_ids[ancient.suit], idol_suit=suit_ids[idol.suit],
            idol_rank=type(id)=='number' and id >= 2 and id <= 14 and (id == 14 and 1 or id) or nil,
            normal_probability=(G.GAME.probabilities or {}).normal or 1, params={}, owned={}}
        local signature = {tostring(ctx.ancient_suit),tostring(ctx.idol_suit),tostring(ctx.idol_rank),tostring(ctx.normal_probability)}
        local by_key = {}
        local function append(params)
            for _, key in ipairs({'mult','chips','x','odds'}) do signature[#signature+1] = tostring(params[key]) end
        end
        for _, spec in ipairs(specs) do
            by_key[spec.key] = spec
            local centre = (G.P_CENTERS or {})[spec.key]
            ctx.params[spec.key] = read_params(spec, centre and centre.config)
            append(ctx.params[spec.key])
        end
        for i, card in ipairs(G.jokers and G.jokers.cards or {}) do
            local key = card.config and card.config.center and card.config.center.key
            if by_key[key] then
                local params = read_params(by_key[key], card.ability)
                ctx.owned[#ctx.owned+1] = {index=i,key=key,debuff=not not card.debuff,params=params}
                signature[#signature+1] = i .. ':' .. key .. ':' .. tostring(not not card.debuff)
                append(params)
            end
        end
        return ctx, table.concat(signature, ',')
    end
    local function type_joint(result, hand, trigger)
        if subtypes[hand][trigger] then return result.marginal[hand] end
        if hand == 'flush' and result.flush_contains[trigger] then return result.flush_contains[trigger] end
        if (hand == 'flush' and trigger == 'straight') or (hand == 'straight' and trigger == 'flush') then return result.marginal.straight_flush end
        if hand == 'full_house' and trigger == 'flush' then return result.marginal.flush_house end
        if hand == 'five' and trigger == 'flush' then return result.marginal.flush_five end
        return 0
    end
    local function one(result, events, ctx, spec, params, debuff)
            local out = {}
            if debuff then
                for _, hand in ipairs(kinds) do out[hand] = {mult=0,chips=0,xmult=spec.x and 1 or 0} end
                return out, 'ready'
            end
            if spec.query and not result.target_distributions[spec.query] then return out, 'target_unavailable' end
            local values = {}
            for _, key in ipairs({'mult','chips','x','odds'}) do values[key] = params[key] or spec[key] or 0 end
            for _, hand in ipairs(kinds) do
                -- Every non-activation outcome contributes the neutral factor 1,
                -- including draws that cannot form this hand. Add only excess.
                local count, trigger, x = 0, 0, spec.x and 1 or 0
                if spec.query then
                    local hist = result.target_distributions[spec.query][hand]
                    for j = 1, 5 do
                        local p = hist[j+1]
                        count, trigger = count + j * p, trigger + p
                        if spec.x then
                            if spec.key == 'j_bloodstone' then
                                local chance = values.odds > 0 and math.min(1,math.max(0,(ctx.normal_probability or 1)/values.odds)) or 0
                                x = x + p * ((1 + chance*(values.x-1))^j - 1)
                            elseif spec.once then x = x + p * (values.x - 1)
                            else x = x + p * (values.x^j - 1) end
                        end
                    end
                    -- Reuse the existing conditional greedy arrays for linear,
                    -- single-suit/single-rank rewards. Sets and powers need histograms.
                    if suits[spec.query] then count = result.marginal[hand] * result.suit_expected_counts[hand][suits[spec.query]]
                    elseif spec.query == 'aces' then count = result.marginal[hand] * result.rank_expected_counts[hand][1] end
                else
                    trigger = spec.event and events[spec.event][hand] or type_joint(result,hand,spec.trigger)
                    count, x = trigger, spec.x and (1 + (values.x - 1) * trigger) or 0
                end
                out[hand] = {mult=values.mult*count, chips=values.chips*count, xmult=x}
            end
            return out, 'ready'
    end
    -- Hovered shop cards and duplicate owned cards use the actual instance's
    -- ability, without replacing the cached catalog or another instance's f.
    function J.for_card(result, card)
        local key = card.config and card.config.center and card.config.center.key
        for _, spec in ipairs(specs) do
            if spec.key == key then
                return one(result, result.joker_events, result.joker_context or {},
                    spec, read_params(spec, card.ability), card.debuff)
            end
        end
        return nil, 'unsupported'
    end
    function J.evaluate(result, events, ctx)
        ctx = ctx or {}
        result.joker_f, result.joker_status, result.owned_joker_f = {}, {}, {}
        local by_key = {}
        for _, spec in ipairs(specs) do
            by_key[spec.key] = spec
            result.joker_f[spec.key], result.joker_status[spec.key] = one(result,events,ctx,spec,(ctx.params or {})[spec.key] or {})
        end
        for _, card in ipairs(ctx.owned or {}) do
            if by_key[card.key] then
                local values, ready = one(result,events,ctx,by_key[card.key],card.params or {},card.debuff)
                result.owned_joker_f[#result.owned_joker_f+1] = {index=card.index,key=card.key,by_hand=values,status=ready}
            end
        end
        result.joker_f_model, result.joker_events = 'unconditional_expected_multiplier_per_core_hand', events
        result.joker_context = ctx
        return result
    end
    return J
end
