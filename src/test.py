stack = []
input = [5,3,2,10,6,8,1,12,7,4]
result = {}
for i in input:
    result[i] = -1
print(result)
for i in range(len(input)):
    if len(stack) == 0:
        stack.append(input[i])
        print(stack)
        continue
    if input[i] > stack[-1]:
        j=i
        while len(stack) != 0 and input[i] > stack[-1]:
            result[stack[-1]] = input[i]
            stack.pop()
            j-=1
        stack.append(input[i])
        print(stack)
        continue
    stack.append(input[i])
    print(stack)
print(result.values())