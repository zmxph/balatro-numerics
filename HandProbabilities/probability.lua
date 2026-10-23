-- Factory is serializable with string.dump: the worker gets its own Lua state.
-- Port of card_type_probs.py's contains/anchor model. No random sampling.
return function()
    local bit = require('bit')
    local band, bor, bnot = bit.band, bit.bor, bit.bnot
    local min, floor = math.min, math.floor
    local P = {}
    P.kinds = {'pair', 'two_pair', 'three', 'four', 'five', 'full_house',
        'flush', 'straight', 'straight_flush', 'flush_house', 'flush_five', 'high_card'}

    local function zeros()
        local a = {}
        for s = 1, 4 do a[s] = {}; for r = 1, 13 do a[s][r] = 0 end end
        return a
    end

    -- Whole-suit/rank objectives must be optimized before averaging. Summing
    -- cell maxima would combine mutually exclusive choices of played core.
    local function grouped(M, k, marginal, C, den, queries)
        local ranks, suits, n = {}, {}, 0
        for r = 1, 13 do ranks[r] = 0 end
        for s = 1, 4 do
            suits[s] = 0
            for r = 1, 13 do
                ranks[r], suits[s], n = ranks[r] + M[s][r], suits[s] + M[s][r], n + M[s][r]
            end
        end
        local max = math.max
        local shapes = {pair = {2}, two_pair = {2, 2}, three = {3}, four = {4}, five = {5}, full_house = {2, 3}}
        local function add(dp, t, st, w)
            if w == 0 then return end
            local row = dp[t] or {}; dp[t] = row
            row[st] = (row[st] or 0) + w
        end
        local function impossible(count)
            local dp = {}
            for t = 0, min(count, k) do dp[t] = {[-1] = C(count, t)} end
            return dp
        end
        local cache = {}
        local function pattern(counts, targets, shape)
            local a, b = shape[1], shape[2]
            local can, count, keys = false, 0, {}
            for r = 1, 13 do
                count = count + counts[r]
                keys[r] = counts[r] .. ':' .. targets[r]
                if counts[r] >= a then
                    if not b then can = true else
                        for rr = 1, 13 do if rr ~= r and counts[rr] >= b then can = true end end
                    end
                end
            end
            if not can or a + (b or 0) > k then return impossible(count) end
            table.sort(keys)
            local key = a .. ':' .. (b or 0) .. '/' .. table.concat(keys, ',')
            if cache[key] then return cache[key] end
            -- Each component stores best score + 1 (zero means impossible).
            -- Two-slot states retain each single role and the best completed core.
            local dp = {[0] = {[0] = 1}}
            for r = 1, 13 do
                local c, target = counts[r], targets[r]
                if c > 0 then
                    local options = {}
                    for j = 0, min(target, k) do
                        for other = 0, min(c - target, k - j) do
                            add(options, j + other, min(j, 5), C(target, j) * C(c - target, other))
                        end
                    end
                    local ndp = {}
                    for t, states in pairs(dp) do
                        for take, choices in pairs(options) do
                            if t + take <= k then
                                for j, weight in pairs(choices) do
                                    local sa = take >= a and min(j, a) + 1 or 0
                                    local sb = b and take >= b and min(j, b) + 1 or 0
                                    for st, ways in pairs(states) do
                                        local new
                                        if not b then new = max(st, sa) else
                                            local first, second, both = st % 7, floor(st / 7) % 7, floor(st / 49)
                                            if first > 0 and sb > 0 then both = max(both, first + sb - 1) end
                                            if second > 0 and sa > 0 then both = max(both, second + sa - 1) end
                                            new = max(first, sa) + 7 * max(second, sb) + 49 * both
                                        end
                                        add(ndp, t + take, new, ways * weight)
                                    end
                                end
                            end
                        end
                    end
                    dp = ndp
                end
            end
            local out = {}
            for t, states in pairs(dp) do for st, ways in pairs(states) do
                add(out, t, (b and floor(st / 49) or st) - 1, ways)
            end end
            cache[key] = out
            return out
        end
        local history_score = {}
        for h = 0, 80 do
            local x, score = h, 0
            for _ = 1, 4 do
                if x % 3 == 0 then score = -1; break end
                if x % 3 == 2 then score = score + 1 end
                x = floor(x / 3)
            end
            history_score[h] = score
        end
        local function straight(counts, targets)
            -- Last four ternary tokens, ace token, best completed window + 1.
            -- 0 absent, 1 present without target, 2 target available.
            local dp = {[0] = {[0] = 1}}
            for r = 1, 13 do
                local ndp, options = {}, {[0] = {[0] = 1}}
                for take = 1, min(counts[r], k) do
                    local without = C(counts[r] - targets[r], take)
                    options[take] = {[1] = without, [2] = C(counts[r], take) - without}
                end
                for t, states in pairs(dp) do
                    for take, choices in pairs(options) do if t + take <= k then
                        for token, weight in pairs(choices) do if weight > 0 then
                            for st, ways in pairs(states) do
                                local h, ace, best = st % 81, floor(st / 81) % 3, floor(st / 243)
                                if token > 0 and history_score[h] >= 0 then
                                    best = max(best, history_score[h] + (token == 2 and 1 or 0) + 1)
                                end
                                local new = (h % 27) * 3 + token + 81 * (r == 1 and token or ace) + 243 * best
                                add(ndp, t + take, new, ways * weight)
                            end
                        end end
                    end end
                end
                dp = ndp
            end
            local out = {}
            for t, states in pairs(dp) do for st, ways in pairs(states) do
                local h, ace, best = st % 81, floor(st / 81) % 3, floor(st / 243) - 1
                if ace > 0 and history_score[h] >= 0 then best = max(best, history_score[h] + (ace == 2 and 1 or 0)) end
                add(out, t, best, ways)
            end end
            return out
        end
        local function flush_target(s, target)
            local dp = {}
            for t = 0, min(suits[s], k) do
                for j = 0, min(target, t) do
                    add(dp, t, t >= 5 and min(j, 5) or -1, C(target, j) * C(suits[s] - target, t - j))
                end
            end
            return dp
        end
        local function weighted(dp, outside, event)
            local sum = 0
            for t, states in pairs(dp) do for score, ways in pairs(states) do
                local value = event and (score >= 0 and 1 or 0) or max(0, score)
                sum = sum + value * ways * C(outside or 0, k - t)
            end end
            assert(sum == sum and sum < math.huge, 'Non-finite grouped expectation')
            return sum / den
        end
        local function best_suit(rows, raw)
            local dp = {[0] = {[-1] = 1}}
            for s = 1, 4 do
                local ndp = {}
                for t, states in pairs(dp) do
                    for take, choices in pairs(rows[s]) do if t + take <= k then
                        for score, ways in pairs(states) do for other, weight in pairs(choices) do
                            add(ndp, t + take, max(score, other), ways * weight)
                        end end
                    end end
                end
                dp = ndp
            end
            return raw and dp or weighted(dp)
        end
        local suit_values, rank_values, zero_targets = {}, {}, {}
        for _, kind in ipairs(P.kinds) do suit_values[kind], rank_values[kind] = {}, {} end
        for r = 1, 13 do zero_targets[r] = 0 end
        for s = 1, 4 do
            for kind, shape in pairs(shapes) do suit_values[kind][s] = weighted(pattern(ranks, M[s], shape)) end
            suit_values.straight[s] = weighted(straight(ranks, M[s]))
            local sum = 0
            for t = 5, min(suits[s], k) do sum = sum + C(suits[s], t) * C(n - suits[s], k - t) end
            suit_values.flush[s] = 5 * sum / den
            suit_values.straight_flush[s] = 5 * weighted(straight(M[s], zero_targets), n - suits[s], true)
            suit_values.flush_house[s] = 5 * weighted(pattern(M[s], zero_targets, {2, 3}), n - suits[s], true)
            suit_values.flush_five[s] = 5 * weighted(pattern(M[s], zero_targets, {5}), n - suits[s], true)
            suit_values.high_card[s] = (den - C(n - suits[s], k)) / den
        end
        for r = 1, 13 do
            local target = {}
            for rr = 1, 13 do target[rr] = rr == r and ranks[r] or 0 end
            for kind, shape in pairs(shapes) do rank_values[kind][r] = weighted(pattern(ranks, target, shape)) end
            rank_values.straight[r] = weighted(straight(ranks, target))
            rank_values.high_card[r] = (den - C(n - ranks[r], k)) / den
            local rows, straights, houses, fives = {}, {}, {}, {}
            for s = 1, 4 do
                rows[s] = flush_target(s, M[s][r])
                for rr = 1, 13 do target[rr] = rr == r and M[s][r] or 0 end
                straights[s] = straight(M[s], target)
                houses[s] = pattern(M[s], target, {2, 3})
                fives[s] = pattern(M[s], target, {5})
            end
            rank_values.flush[r] = best_suit(rows)
            rank_values.straight_flush[r] = best_suit(straights)
            rank_values.flush_house[r] = best_suit(houses)
            rank_values.flush_five[r] = best_suit(fives)
        end
        for _, kind in ipairs(P.kinds) do
            local p = marginal[kind]
            for s = 1, 4 do suit_values[kind][s] = p > 0 and suit_values[kind][s] / p or 0 end
            for r = 1, 13 do rank_values[kind][r] = p > 0 and rank_values[kind][r] / p or 0 end
        end
        local distributions, flush_contains = {}, {}
        if queries then
            local function histogram(dp)
                local h = {}
                for j = 0, 5 do h[j + 1] = ((dp[k] or {})[j] or 0) / den end
                return h
            end
            for name, target in pairs(queries) do
                local totals, count = {}, 0
                for r = 1, 13 do
                    totals[r] = 0
                    for s = 1, 4 do
                        assert(target[s][r] >= 0 and target[s][r] <= M[s][r], 'Invalid target count')
                        totals[r], count = totals[r] + target[s][r], count + target[s][r]
                    end
                end
                local hist = {}
                for kind, shape in pairs(shapes) do hist[kind] = histogram(pattern(ranks, totals, shape)) end
                hist.straight = histogram(straight(ranks, totals))
                hist.high_card = {0, 0, 0, 0, 0, 0}
                if k > 0 then
                    hist.high_card[1] = C(n - count, k) / den
                    hist.high_card[2] = 1 - hist.high_card[1]
                end
                local rows = {flush = {}, straight_flush = {}, flush_house = {}, flush_five = {}}
                for s = 1, 4 do
                    local total = 0
                    for r = 1, 13 do total = total + target[s][r] end
                    rows.flush[s] = flush_target(s, total)
                    rows.straight_flush[s] = straight(M[s], target[s])
                    rows.flush_house[s] = pattern(M[s], target[s], {2, 3})
                    rows.flush_five[s] = pattern(M[s], target[s], {5})
                end
                for kind, ds in pairs(rows) do hist[kind] = histogram(best_suit(ds, true)) end
                distributions[name] = hist
            end
            for _, kind in ipairs({'pair', 'two_pair', 'three', 'four'}) do
                local rows = {}
                for s = 1, 4 do
                    rows[s] = {}
                    for t, states in pairs(pattern(M[s], zero_targets, shapes[kind])) do
                        for score, ways in pairs(states) do add(rows[s], t, t >= 5 and score >= 0 and 1 or 0, ways) end
                    end
                end
                flush_contains[kind] = best_suit(rows)
            end
        end
        return suit_values, rank_values, distributions, flush_contains
    end

    function P.compute(M, requested_k, publish, queries)
        local ranks, suits, n = {}, {}, 0
        for r = 1, 13 do ranks[r] = 0 end
        for s = 1, 4 do
            suits[s] = 0
            for r = 1, 13 do
                local c = M[s][r]
                assert(type(c) == 'number' and c >= 0 and c == floor(c), 'Invalid deck count')
                ranks[r], suits[s], n = ranks[r] + c, suits[s] + c, n + c
            end
        end
        local k = min(n, math.max(0, math.ceil(requested_k)))
        local C = {}
        local function choose(a, b)
            if b < 0 or b > a then return 0 end
            return C[a][b] or 0
        end
        for a = 0, n do
            C[a] = {[0] = 1}
            for b = 1, min(a, k) do
                C[a][b] = (C[a - 1][b - 1] or 0) + (C[a - 1][b] or 0)
            end
        end
        local den = choose(n, k)
        assert(den < math.huge, 'Deck/sample too large for floating-point DP')
        local function probability(w)
            assert(w == w and w < math.huge, 'Non-finite DP result')
            return math.max(0, min(1, w / den))
        end
        local result = {marginal = {}, matrices = {}, expected_counts = {},
            unconditional_counts = {}, n = n, k = k,
            model = 'contains_base_rules', anchor = 'at_least_one_copy_of_suit_rank',
            expectation_model = 'max_core_copies_given_hand_formable',
            impossible_expectation = 'zero_by_convention'}
        for _, kind in ipairs(P.kinds) do
            result.marginal[kind], result.matrices[kind] = 0, zeros()
            result.expected_counts[kind], result.unconditional_counts[kind] = zeros(), zeros()
        end

        -- Generic count/state DP. Counts are ordinary doubles, not Monte Carlo.
        local function distribution(groups, initial, transition, weight)
            local dp = {[0] = {[initial] = 1}}
            for i, count in ipairs(groups) do
                local next_dp = {}
                for t, states in pairs(dp) do
                    for take = 0, min(count, k - t) do
                        local w = weight and weight(i, count, take) or choose(count, take)
                        if w > 0 then
                            local dest = next_dp[t + take] or {}
                            next_dp[t + take] = dest
                            for state, ways in pairs(states) do
                                local target = transition(state, take, i)
                                dest[target] = (dest[target] or 0) + ways * w
                            end
                        end
                    end
                end
                dp = next_dp
            end
            return dp
        end
        local function total(dp, accept, outside)
            local w = 0
            for t, states in pairs(dp) do
                local extra = choose(outside or 0, k - t)
                if extra > 0 then
                    for state, ways in pairs(states) do
                        if accept(state) then w = w + ways * extra end
                    end
                end
            end
            return probability(w)
        end
        -- State: pair ranks capped at two; bits: trip, quad, five.
        local function rank_step(state, take)
            local pairs = state % 3
            local flags = floor(state / 3)
            if take >= 2 then pairs = min(2, pairs + 1) end
            if take >= 3 then flags = bor(flags, 1) end
            if take >= 4 then flags = bor(flags, 2) end
            if take >= 5 then flags = bor(flags, 4) end
            return pairs + 3 * flags
        end
        local accepts = {
            pair = function(st) return st % 3 >= 1 end,
            two_pair = function(st) return st % 3 >= 2 end,
            three = function(st) return band(floor(st / 3), 1) ~= 0 end,
            four = function(st) return band(floor(st / 3), 2) ~= 0 end,
            five = function(st) return band(floor(st / 3), 4) ~= 0 end,
            full_house = function(st) return st % 3 >= 2 and band(floor(st / 3), 1) ~= 0 end,
        }
        local rd = distribution(ranks, 0, rank_step)
        for kind, accept in pairs(accepts) do result.marginal[kind] = total(rd, accept) end

        -- A,2,...,K and TJQKA. No illegal K,A,2,3,4 wraparound.
        local kill, all_windows = {}, 1023
        for r = 1, 13 do kill[r] = 0 end
        for w = 0, 9 do
            for offset = 0, 4 do
                local r = w + offset + 1
                if r == 14 then r = 1 end
                kill[r] = bor(kill[r], 2 ^ w)
            end
        end
        local function straight_step(mask, take, r)
            return take == 0 and band(mask, bnot(kill[r])) or mask
        end
        local alive = function(mask) return mask ~= 0 end
        result.marginal.straight = total(distribution(ranks, all_windows, straight_step), alive)

        -- Count the union over suits directly, avoiding cancellation for tiny odds.
        local function suit_union(row_distribution, accept)
            local dp = {[0] = {[0] = 1}}
            for s = 1, 4 do
                local grouped = {}
                for t, states in pairs(row_distribution(s)) do
                    grouped[t] = {[0] = 0, [1] = 0}
                    for st, w in pairs(states) do
                        local yes = accept(st, t) and 1 or 0
                        grouped[t][yes] = grouped[t][yes] + w
                    end
                end
                local next_dp = {}
                for t, states in pairs(dp) do
                    for take, row in pairs(grouped) do
                        if t + take <= k then
                            local dst = next_dp[t + take] or {[0] = 0, [1] = 0}
                            next_dp[t + take] = dst
                            for yes, w in pairs(states) do
                                for row_yes, w2 in pairs(row) do
                                    local target = math.max(yes, row_yes)
                                    dst[target] = dst[target] + w * w2
                                end
                            end
                        end
                    end
                end
                dp = next_dp
            end
            return probability(dp[k] and dp[k][1] or 0)
        end
        result.marginal.flush = suit_union(function(s)
            local row = {}
            for t = 0, min(suits[s], k) do row[t] = {[0] = choose(suits[s], t)} end
            return row
        end, function(_, t) return t >= 5 end)
        result.marginal.straight_flush = suit_union(function(s)
            return distribution(M[s], all_windows, straight_step)
        end, alive)
        result.marginal.flush_house = suit_union(function(s)
            return distribution(M[s], 0, rank_step)
        end, accepts.full_house)
        result.marginal.flush_five = suit_union(function(s)
            return distribution(M[s], 0, rank_step)
        end, accepts.five)
        result.marginal.high_card = k > 0 and 1 or 0
        if publish then publish(result.marginal, n, k) end

        -- At least one of the copies in cell (s,r) must be drawn. This matches
        -- the Python matrices; it is not the probability for a unique physical copy.
        local function anchored_weight(anchor, copies)
            return function(i, count, take)
                if i == anchor then return choose(count, take) - choose(count - copies, take) end
                return choose(count, take)
            end
        end
        for r = 1, 13 do
            local others = {}
            for rr = 1, 13 do if rr ~= r then others[#others + 1] = ranks[rr] end end
            local other_dp = distribution(others, 0, rank_step)
            for s = 1, 4 do
                local copies = M[s][r]
                if copies > 0 then
                    local nums = {pair = 0, two_pair = 0, three = 0, four = 0, five = 0, full_house = 0}
                    local count_nums = {pair = 0, two_pair = 0, three = 0, four = 0, five = 0, full_house = 0}
                    for take = 1, min(ranks[r], k) do
                        local w = choose(ranks[r], take) - choose(ranks[r] - copies, take)
                        -- Split out target-cell copies. Existence alone loses the
                        -- distinction between one target card and two or more.
                        local capped_weights = {}
                        for cap = 2, 5 do
                            local sum = 0
                            for j = 1, min(copies, take) do
                                sum = sum + min(j, cap) * choose(copies, j) * choose(ranks[r] - copies, take - j)
                            end
                            capped_weights[cap] = sum
                        end
                        for st, rest in pairs(other_dp[k - take] or {}) do
                            local o2, o3 = accepts.pair(st), accepts.three(st)
                            local hit = {pair = take >= 2, two_pair = take >= 2 and o2,
                                three = take >= 3, four = take >= 4, five = take >= 5,
                                full_house = (take >= 3 and o2) or (take >= 2 and o3)}
                            for kind, yes in pairs(hit) do if yes then nums[kind] = nums[kind] + w * rest end end
                            local caps = {pair = 2, two_pair = 2, three = 3, four = 4, five = 5,
                                full_house = (take >= 3 and o2) and 3 or 2}
                            for kind, yes in pairs(hit) do
                                if yes then count_nums[kind] = count_nums[kind] + capped_weights[caps[kind]] * rest end
                            end
                        end
                    end
                    for kind, w in pairs(nums) do result.matrices[kind][s][r] = probability(w) end
                    for kind, w in pairs(count_nums) do result.unconditional_counts[kind][s][r] = w / den end
                    local flush_num, five_num, seen_num = 0, 0, 0
                    local flush_count_num = 0
                    for take = 1, min(copies, k) do
                        local w = choose(copies, take) * choose(n - copies, k - take)
                        seen_num = seen_num + w
                        if take >= 5 then five_num = five_num + w end
                        for other = math.max(0, 5 - take), min(suits[s] - copies, k - take) do
                            flush_count_num = flush_count_num + min(take, 5) * choose(copies, take)
                                * choose(suits[s] - copies, other) * choose(n - suits[s], k - take - other)
                        end
                    end
                    for take = 5, min(suits[s], k) do
                        flush_num = flush_num + (choose(suits[s], take) - choose(suits[s] - copies, take))
                            * choose(n - suits[s], k - take)
                    end
                    result.matrices.flush[s][r] = probability(flush_num)
                    result.matrices.flush_five[s][r] = probability(five_num)
                    result.matrices.high_card[s][r] = probability(seen_num)
                    result.matrices.straight[s][r] = total(distribution(ranks, kill[r], straight_step,
                        anchored_weight(r, copies)), alive)
                    result.matrices.straight_flush[s][r] = total(distribution(M[s], kill[r], straight_step,
                        anchored_weight(r, copies)), alive, n - suits[s])
                    result.unconditional_counts.flush[s][r] = flush_count_num / den
                    result.unconditional_counts.flush_five[s][r] = 5 * result.matrices.flush_five[s][r]
                    -- A straight uses each rank once; a high-card core has one card.
                    for _, kind in ipairs({'straight', 'straight_flush', 'high_card'}) do
                        result.unconditional_counts[kind][s][r] = result.matrices[kind][s][r]
                    end
                    local row_others = {}
                    for rr = 1, 13 do if rr ~= r then row_others[#row_others + 1] = M[s][rr] end end
                    local row_dp = distribution(row_others, 0, rank_step)
                    local house_num, house_count_num = 0, 0
                    for take = 2, min(copies, k) do
                        for t, states in pairs(row_dp) do
                            local w = choose(copies, take) * choose(n - suits[s], k - take - t)
                            if w > 0 then
                                for st, ways in pairs(states) do
                                    if (take >= 3 and accepts.pair(st)) or accepts.three(st) then
                                        house_num = house_num + w * ways
                                        -- When both 3+2 assignments work, maximize
                                        -- this cell independently: choose its triplet.
                                        local cap = (take >= 3 and accepts.pair(st)) and 3 or 2
                                        house_count_num = house_count_num + min(take, cap) * w * ways
                                    end
                                end
                            end
                        end
                    end
                    result.matrices.flush_house[s][r] = probability(house_num)
                    result.unconditional_counts.flush_house[s][r] = house_count_num / den
                end
            end
        end
        -- Conditioning is on T being formable anywhere, not on the target card
        -- being present. Draws forming T without this target contribute zero.
        for _, kind in ipairs(P.kinds) do
            local p = result.marginal[kind]
            for s = 1, 4 do for r = 1, 13 do
                local u = result.unconditional_counts[kind][s][r]
                assert(u == u and u < math.huge, 'Non-finite expected count')
                result.expected_counts[kind][s][r] = p > 0 and u / p or 0
            end end
        end
        result.suit_expected_counts, result.rank_expected_counts, result.target_distributions, result.flush_contains =
            grouped(M, k, result.marginal, choose, den, queries)
        return result
    end
    return P
end
