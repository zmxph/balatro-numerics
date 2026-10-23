-- Serializable factory for exact multi-suit events in one legal scoring core.
return function()
    local bit = require('bit')
    local band, bor = bit.band, bit.bor
    local min, floor = math.min, math.floor
    local function compute_event(M, k, colours)
        local goal, n = 0, 0
        for s = 1, 4 do
            goal = bor(goal, colours[s])
            for r = 1, 13 do n = n + M[s][r] end
        end
        local bins = {}
        for a = 0, n do
            bins[a] = {[0] = 1}
            for b = 1, min(a, k) do bins[a][b] = (bins[a-1][b-1] or 0) + (bins[a-1][b] or 0) end
        end
        local den, hit = bins[n][k], 2 ^ goal
        local norm_cache, extend_cache, masks_cache = {}, {}, {}
        local supersets = {}
        for m = 0, goal do
            supersets[m] = 0
            for x = 0, goal do if x ~= m and bor(m, x) == x then supersets[m] = supersets[m] + 2 ^ x end end
        end
        local function normalize(bits)
            if norm_cache[bits] then return norm_cache[bits] end
            local out = 0
            for m = 0, goal do
                if band(bits, 2 ^ m) ~= 0 and band(bits, supersets[m]) == 0 then out = out + 2 ^ m end
            end
            norm_cache[bits] = out
            return out
        end
        local function masks(bits)
            if not masks_cache[bits] then
                local list = {}
                for m = 0, goal do if band(bits, 2 ^ m) ~= 0 then list[#list+1] = m end end
                masks_cache[bits] = list
            end
            return masks_cache[bits]
        end
        local function extend(a, b)
            if a == 0 or b == 0 then return 0 end
            if b < a then a, b = b, a end
            local key = a + 65536 * b
            if extend_cache[key] then return extend_cache[key] end
            local out = 0
            for _, x in ipairs(masks(a)) do for _, y in ipairs(masks(b)) do out = bor(out, 2 ^ bor(x, y)) end end
            out = normalize(out)
            extend_cache[key] = out
            return out
        end
        local choice_cache = {}
        local function choices(counts)
            local key = 0
            for s = 1, 4 do key = key * 6 + min(5, counts[s]) end
            if choice_cache[key] then return choice_cache[key] end
            local dp = {[0] = 1}
            for s = 1, 4 do
                local ndp = {}
                for t, bits in pairs(dp) do
                    for j = 0, min(counts[s], 5-t) do
                        local v = extend(bits, 2 ^ (j > 0 and colours[s] or 0))
                        ndp[t+j] = normalize(bor(ndp[t+j] or 0, v))
                    end
                end
                dp = ndp
            end
            local out = {}
            for j = 1, 5 do out[j] = dp[j] or 0 end
            choice_cache[key] = out
            return out
        end
        local options = {}
        for r = 1, 13 do
            local combined, counts = {}, {}
            local function visit(s, t, weight)
                if s == 5 then
                    local c = choices(counts)
                    local key = t .. ':' .. table.concat(c, ':')
                    if combined[key] then combined[key].weight = combined[key].weight + weight
                    else combined[key] = {take = t, choices = c, weight = weight} end
                    return
                end
                for take = 0, min(M[s][r], k-t) do
                    counts[s] = take
                    visit(s+1, t+take, weight * bins[M[s][r]][take])
                end
            end
            visit(1, 0, 1)
            options[r] = {}
            for _, option in pairs(combined) do options[r][#options[r]+1] = option end
        end
        local function add(dp, t, st, w)
            local row = dp[t] or {}; dp[t] = row
            row[st] = (row[st] or 0) + w
        end
        local colour_count = goal == 15 and 4 or 2
        local function shape_event(a, b)
            if a + (b or 0) < colour_count then return 0 end
            local dp, transitions = {[0] = {[0] = 1}}, {}
            for r = 1, 13 do
                local ndp = {}
                for _, option in ipairs(options[r]) do
                    local ca, cb = option.choices[a], b and option.choices[b] or 0
                    local token = ca + 65536 * cb
                    local cache = transitions[token] or {}; transitions[token] = cache
                    for t, states in pairs(dp) do if t + option.take <= k then
                        for st, ways in pairs(states) do
                            local new = cache[st]
                            if new == nil then
                                local first, second = st % 65536, floor(st / 65536)
                                local success = st == -1 or (not b and band(ca, hit) ~= 0) or
                                    (b and band(bor(extend(first, cb), extend(second, ca)), hit) ~= 0)
                                new = success and -1 or normalize(bor(first, ca)) + 65536 * normalize(bor(second, cb))
                                cache[st] = new
                            end
                            add(ndp, t + option.take, new, ways * option.weight)
                        end
                    end end
                end
                dp = ndp
            end
            return ((dp[k] or {})[-1] or 0) / den
        end
        local function straight_event()
            local states, ids, transitions = {}, {}, {}
            local function intern(ace, a, b, c, d)
                local key = ace .. ':' .. a .. ':' .. b .. ':' .. c .. ':' .. d
                if not ids[key] then
                    states[#states+1] = {ace, a, b, c, d}
                    ids[key] = #states
                end
                return ids[key]
            end
            local dp = {[0] = {[intern(0, 0, 0, 0, 0)] = 1}}
            for r = 1, 13 do
                local opts, ndp = {}, {}
                for _, option in ipairs(options[r]) do
                    local token = option.choices[1]
                    add(opts, option.take, token, option.weight)
                end
                for take, choices_by_token in pairs(opts) do for token, weight in pairs(choices_by_token) do
                    local cache_key = token + (r == 1 and 65536 or 0)
                    local cache = transitions[cache_key] or {}; transitions[cache_key] = cache
                    for t, current in pairs(dp) do if t + take <= k then
                        for id, ways in pairs(current) do
                            local new = cache[id]
                            if new == nil then
                                if id == -1 or band(extend(states[id][5], token), hit) ~= 0 then new = -1 else
                                    local st = states[id]
                                    new = intern(r == 1 and token or st[1], token, extend(st[2], token), extend(st[3], token), extend(st[4], token))
                                end
                                cache[id] = new
                            end
                            add(ndp, t+take, new, ways * weight)
                        end
                    end end
                end end
                dp = ndp
            end
            local sum = 0
            for id, ways in pairs(dp[k] or {}) do
                if id == -1 or band(extend(states[id][5], states[id][1]), hit) ~= 0 then sum = sum + ways end
            end
            return sum / den
        end
        return {pair = shape_event(2), two_pair = shape_event(2, 2), three = shape_event(3),
            four = shape_event(4), five = shape_event(5), full_house = shape_event(2, 3),
            straight = straight_event(), flush = 0, straight_flush = 0, flush_house = 0, flush_five = 0, high_card = 0}
    end
    return {compute = function(M, k)
        return {flower_pot = compute_event(M, k, {1, 2, 4, 8}), seeing_double = compute_event(M, k, {2, 2, 1, 2})}
    end}
end
