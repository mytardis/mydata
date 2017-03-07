# Makefile for add-loginitem, delete-loginitem and loginitem-exists

SRCDIR=src
OBJDIR=obj
BINDIR=bin

all: add-loginitem delete-loginitem loginitem-exists

add-loginitem: $(OBJDIR)/add-loginitem.o $(OBJDIR)/LaunchAtLoginController.o objdir
	gcc -o $(BINDIR)/add-loginitem -framework Foundation -framework AppKit \
	$(OBJDIR)/add-loginitem.o $(OBJDIR)/LaunchAtLoginController.o

delete-loginitem: $(OBJDIR)/delete-loginitem.o $(OBJDIR)/LaunchAtLoginController.o objdir
	gcc -o $(BINDIR)/delete-loginitem -framework Foundation -framework AppKit \
	$(OBJDIR)/delete-loginitem.o $(OBJDIR)/LaunchAtLoginController.o

loginitem-exists: $(OBJDIR)/loginitem-exists.o $(OBJDIR)/LaunchAtLoginController.o objdir
	gcc -o $(BINDIR)/loginitem-exists -framework Foundation -framework AppKit \
	$(OBJDIR)/loginitem-exists.o $(OBJDIR)/LaunchAtLoginController.o

$(OBJDIR)/add-loginitem.o: $(SRCDIR)/add-loginitem.m objdir
	gcc -o $(OBJDIR)/add-loginitem.o -c $(SRCDIR)/add-loginitem.m

$(OBJDIR)/delete-loginitem.o: $(SRCDIR)/delete-loginitem.m objdir
	gcc -o $(OBJDIR)/delete-loginitem.o -c $(SRCDIR)/delete-loginitem.m

$(OBJDIR)/loginitem-exists.o: $(SRCDIR)/loginitem-exists.m objdir
	gcc -o $(OBJDIR)/loginitem-exists.o -c $(SRCDIR)/loginitem-exists.m

$(OBJDIR)/LaunchAtLoginController.o: $(SRCDIR)/LaunchAtLoginController/LaunchAtLoginController.m objdir
	gcc -o $(OBJDIR)/LaunchAtLoginController.o \
	-c $(SRCDIR)/LaunchAtLoginController/LaunchAtLoginController.m

objdir:
	mkdir -p $(OBJDIR)

