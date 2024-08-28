def take_feedback():
    feedback_input = input("Was the above recommendation helpful? If Yes, Type YES if Not press NO")
    if feedback_input.lower() in ['yes', 'y']:
        prompt = "The above recommendation was helpful with the logs supplied. Please save this recommendation for future such logs/occurences"
    if feedback_input.lower() in ['no', 'n']:
        feedback_input_2 = input("Please provide the details for worked for you including the parameters changed and the steps followed:")
        prompt = "The above recommendation provided did not prove to be useful. Rather I followed the below steps to make it work \n {}".format(feedback_input_2)

    return prompt