#install.packages("pdftools")
#install.packages("readxl")
library(pdftools)
library(readxl)

# Format data for csv
mkcsv = function(x){
  # parse the columns by at least two spaces, replace spaces with commas
  tm = gsub("[ ]{2,}",",",x)
  if (length(unlist(strsplit(tm,","))) < 6){
    # correct for rows that missed the correct parsing (at least one per page), replace ending spaces with comma
    # determined based on inspection of the initial results
    tm = gsub(' (?=[^ ]+$)',",",tm, perl=TRUE)
  }
  tm
}


dd = readline(prompt="Enter a directory path: ")
setwd(dd)

# Bring in passwrd data
rrfile = "PZborrowers.xlsx"
rr = read_excel(rrfile,col_names=c("name","pass","date"),skip=2,col_types=rep("text",3))

d = "PZstatements/"
ff = list.files(d)

for (f in ff){
  nn = gsub(".[^.]*$","",f)  # get user name
  pp = rr$pass[rr$name==nn] # open pass
  fi = pdf_text(paste0(d,f),upw=pp)  # read in pdf as text

  lines=c()
  for (p in 1:length(fi)){
    inp = gsub(",","",fi[p])  # get rid of commas in balance data -- for csv compatibility
    ll = strsplit(inp,"\n")   # split on lines
    # Find transactions, identified by alphanumeric string of 10 length
    ll = lapply(ll,grep,pattern="^[A-Z0-9]{10}\\s",value=TRUE)[[1]]
    xx = unlist(lapply(ll,mkcsv))
    lines = c(lines,xx)       # add each line to file for user
  }

  fileConn = file(paste0("data/",pp,".csv"))  # generate file name
  write(paste(lines,collapse="\n"),fileConn)  # save it as a csv
  close(fileConn)
}
