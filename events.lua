local sum = 0
local matches = redis.call('HVALS', 'events')

for _, val in ipairs(matches) do
    sum = sum + tonumber(val)
end

return sum
