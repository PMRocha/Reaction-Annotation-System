print("Starting new script")

#argument path
path = commandArgs()[6]

#loading users and dictionary files
users <- read.table(paste(path,"users.txt",sep=""),header=F,sep=":") 
dictionary <- read.table(paste(path, "dictionary.txt",sep=""),
                         header=F,
                         sep=":",
                         quote = "", 
                         row.names = NULL, 
                         stringsAsFactors = TRUE) 
dictionary[,1] <- as.character(dictionary[,1])

#creating result set data.frame
attributions <- as.data.frame(matrix(0,length(dictionary[,1]),length(dictionary[1,])))

#Algorithm goes here: results go into attributions[TweetID,UserID]

j <- 1
for(i in 1:length(dictionary[,1])){
  attributions[i,1] <- dictionary[i,1]
  attributions[i,2] <- users[j,1]
  if(j == length(users[,1])){
    j <- 1
  }
  else{
    j <- j + 1
  } 
}

#return final attributions
name <- paste(path , "attributions.txt",sep="")
file.create(file=name, showWarnings = TRUE)
new_file <- file(name)
for(i in 1:length(attributions[,1])) {
  text <- paste(attributions[i,1], ":", attributions[i,2],"\n",sep="")
  cat(text,file=name,append=T)
}
close(new_file)
print("Ending script")