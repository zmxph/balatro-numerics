-- Extend the existing popup tree so hover/close/drag lifetime stays vanilla.
return function(H, J, names, active, tr)
    local order = {'Flush Five','Flush House','Five of a Kind','Straight Flush',
        'Four of a Kind','Full House','Flush','Straight','Three of a Kind',
        'Two Pair','Pair','High Card'}
    local specs = {}
    for _, spec in ipairs(J.catalog) do specs[spec.key] = spec end
    local function text(value, scale, colour)
        return {n=G.UIT.T, config={text=value,scale=scale,colour=colour or G.C.WHITE,shadow=true}}
    end
    local function reference(view, key, colour, scale)
        return {n=G.UIT.T, config={ref_table=view,ref_value=key,scale=scale or 0.27,
            colour=colour,shadow=true}}
    end
    local function number(value, prefix)
        if type(value) ~= 'number' or value ~= value or math.abs(value) == math.huge then return '--' end
        return prefix .. string.format('%.1f', math.abs(value) < 0.05 and 0 or value)
    end
    H.format_joker_value = number
    local function update(view, force)
        if not force and view.tick == H.tooltip_tick and view.result == H.result and view.phase == H.status
            and view.debuff == view.card.debuff then return end
        view.tick, view.result, view.phase, view.debuff = H.tooltip_tick, H.result, H.status, view.card.debuff
        local values, status
        if active() and H.status == 'ready' and H.result then values, status = J.for_card(H.result, view.card) end
        local waiting = H.status == 'pending' or H.status == 'calculating' or H.status == 'matrices' or H.status == 'idle'
        local placeholder = waiting and '...' or '--'
        view.status = status == 'ready' and tr('当前牌组 · 基础模型', 'Current deck · Base rules')
            or status == 'target_unavailable' and tr('本回合目标未就绪', 'Round target unavailable')
            or waiting and tr('正在计算…', 'Calculating…') or tr('收益暂不可用', 'Unavailable')
        for _, hand in ipairs(view.hands) do
            local h = G.GAME.hands[hand]
            view[hand .. ':level'] = localize('k_level_prefix') .. tostring(h.level)
            local f = values and values[names[hand]]
            for _, field in ipairs(view.fields) do
                view[hand .. ':' .. field] = f and number(f[field], field == 'xmult' and 'X' or '+') or placeholder
            end
        end
    end
    G.FUNCS.hprob_joker_values = function(e) update(e.config.hprob_view) end
    function H.joker_panel(card)
        local key = card.config and card.config.center and card.config.center.key
        local spec = specs[key]
        local aut = card.ability_UIBox_table
        if not active() or not spec or card.no_ui or card.facing == 'back' or
            (aut and (aut.card_type == 'Locked' or aut.card_type == 'Undiscovered')) then return end
        H.refresh(true)
        local view = {card=card,hands={},fields={}}
        for _, name in ipairs(order) do
            if G.GAME.hands[name] and G.GAME.hands[name].visible then view.hands[#view.hands+1] = name end
        end
        if #view.hands == 0 then return end
        if spec.mult then view.fields[#view.fields+1] = 'mult' end
        if spec.chips then view.fields[#view.fields+1] = 'chips' end
        if spec.x then view.fields[#view.fields+1] = 'xmult' end
        update(view, true)
        local columns = {{n=G.UIT.C,config={align='tm',padding=0.025},nodes={}}}
        local split = math.ceil(#view.hands / 2)
        if #view.hands > 1 then
            columns[2] = {n=G.UIT.B,config={w=0.1,h=0.01}}
            columns[3] = {n=G.UIT.C,config={align='tm',padding=0.025},nodes={}}
        end
        for i, name in ipairs(view.hands) do
            local level = G.GAME.hands[name].level
            local reward = {text('f=',0.27,G.C.WHITE)}
            for j, field in ipairs(view.fields) do
                if j > 1 then reward[#reward+1] = text(' / ',0.22,G.C.WHITE) end
                if field == 'xmult' then
                    reward[#reward+1] = {n=G.UIT.C,config={align='cm',colour=G.C.MULT,r=0.06,padding=0.025},
                        nodes={reference(view,name..':'..field,G.C.WHITE)}}
                else
                    reward[#reward+1] = reference(view,name..':'..field,field == 'chips' and G.C.CHIPS or G.C.MULT)
                end
            end
            local row = {n=G.UIT.R,config={align='cm',padding=0.025,r=0.08,
                colour=darken(G.C.JOKER_GREY,0.1),emboss=0.025},nodes={
                {n=G.UIT.C,config={align='cm',minw=0.62,maxw=0.75,padding=0.015,r=0.07,
                    colour=G.C.HAND_LEVELS[math.max(1,math.min(7,level))],outline=0.5,outline_colour=G.C.WHITE},
                    nodes={reference(view,name..':level',G.C.UI.TEXT_DARK,0.24)}},
                {n=G.UIT.C,config={align='cm',minw=1.02,maxw=1.18},nodes={
                    text(localize(name,'poker_hands'),0.27,G.C.WHITE)}},
                {n=G.UIT.C,config={align='cm',padding=0.035,r=0.07,colour=G.C.L_BLACK,
                    minw=#view.fields > 1 and 1.75 or 1.15,maxw=#view.fields > 1 and 2.05 or 1.5},nodes=reward},
            }}
            local col = i <= split and columns[1] or columns[3]
            col.nodes[#col.nodes+1] = row
        end
        return {n=G.UIT.C,config={id='hprob_joker_panel',align='tm',padding=0.055,r=0.12,
            colour=lighten(G.C.JOKER_GREY,0.5),emboss=0.07,func='hprob_joker_values',hprob_view=view},nodes={
            {n=G.UIT.R,config={align='cm',padding=0.03},nodes={text(tr('牌型收益','Hand returns'),0.30,G.C.WHITE)}},
            {n=G.UIT.R,config={align='tm',padding=0.02,colour=G.C.L_BLACK,r=0.09},nodes=columns},
            {n=G.UIT.R,config={align='cm',padding=0.025},nodes={reference(view,'status',G.C.WHITE,0.20)}},
        }}, view
    end
    local old_popup = G.UIDEF.card_h_popup
    G.UIDEF.card_h_popup = function(card, ...)
        local popup = old_popup(card, ...)
        local panel = popup and popup.nodes and H.joker_panel(card)
        if panel then
            popup.nodes[#popup.nodes+1] = {n=G.UIT.B,config={w=0.12,h=0.01}}
            popup.nodes[#popup.nodes+1] = panel
            popup.config.hprob_has_panel = true
        end
        return popup
    end
    -- The combined description + two-column table must stay on screen, also
    -- for cards in the shop or at the far left/right end of the joker area.
    if Card and Card.align_h_popup then
        local old_align = Card.align_h_popup
        Card.align_h_popup = function(card, ...)
            local alignment = old_align(card, ...)
            if card.config and card.config.h_popup and card.config.h_popup.config.hprob_has_panel then
                alignment.lr_clamp = true
            end
            return alignment
        end
    end
end
