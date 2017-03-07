/*
 * loginitem-exists.m
 * 
 * Checks for application in ~/Library/Preferences/com.apple.loginitems.plist
 *
 * Usage: loginitem-exists /Application/MyApplication.app
 *
 * Exit code: 0 if the application was found in login items
 *            2 if the application was not found in login items
 *            1 if an error occurred
 */

#import <Foundation/Foundation.h>

#import "LaunchAtLoginController/LaunchAtLoginController.h"


int main(int argc, char** argv)
{
    NSArray *args = [[NSProcessInfo processInfo] arguments];
    if ([args count] != 2) {
        fprintf(stderr, "Usage: loginitem-exists /Application/MyApplication.app\n");
        exit(1);
    }
    NSString *appBundlePath = [args objectAtIndex:1];
    NSFileManager *fileManager = [[NSFileManager alloc] init];
    BOOL isDir;
    if (![fileManager fileExistsAtPath:appBundlePath isDirectory:&isDir] || !isDir) {
      fprintf(stderr, "No app bundle was found at: %s\n", argv[1]);
      exit(1);
    }
    LaunchAtLoginController *controller = [[LaunchAtLoginController alloc] init];
    NSURL *appUrl = [NSURL fileURLWithPath:[args objectAtIndex:1]];
    if ([controller willLaunchAtLogin:appUrl]) {
        fprintf(stderr, "%s is currently set to launch at login.\n", argv[1]);
        exit(0);
    }
    else {
        fprintf(stderr, "%s is not currently set to launch at login.\n", argv[1]);
        exit(2);
    }
}
