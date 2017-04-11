/*
 * delete-loginitem.m
 *
 * Deletes application from ~/Library/Preferences/com.apple.loginitems.plist
 *
 * Usage: delete-loginitem /Applications/MyApplication.app
 *
 * Exit code: 0 if the application was successfully deleted from login items
 *            1 if an error occurred
 */

#import <Foundation/Foundation.h>

#import "LaunchAtLoginController/LaunchAtLoginController.h"


int main(int argc, char** argv)
{
  NSArray *args = [[NSProcessInfo processInfo] arguments];
  if ([args count] != 2) {
    fprintf(stderr, "Usage: delete-loginitem /Applications/MyApplication.app\n");
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
  if (![controller willLaunchAtLogin:appUrl]) {
    fprintf(stderr, "WARNING: %s was not set to launch at login.\n", argv[1]);
    exit(1);
  }
  else {
    fprintf(stderr, "%s will no longer launch at login.\n", argv[1]);
    [controller setLaunchAtLogin:NO forURL: appUrl];
    exit(0);
  }
}
