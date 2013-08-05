#!/bin/sh
### BEGIN INIT INFO
# Provides:          arrow-judge
# Required-Start:    $network $local_fs $remote_fs
# Required-Stop:     $remote_fs
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: arrow-judge
# Description:       Arrow-Judge is a open source online judge system.
#                    Arrow-Judge is a open source online judge system, released under MIT License.
#                    This package is the web interface of Arrow-Judge.
### END INIT INFO

# Author: Hiromu Yakura <hiromu1996@gmail.com>

PATH=/sbin:/usr/sbin:/bin:/usr/bin
DESC=arrow-judge
NAME=arrow-judge
DAEMON=/usr/sbin/arrow-judge
PIDFILE=/var/run/$NAME.pid
SCRIPTNAME=/etc/init.d/$NAME

[ -x $DAEMON ] || exit 0
[ -r /etc/default/$NAME ] && . /etc/default/$NAME
. /lib/init/vars.sh
. /lib/lsb/init-functions

do_start()
{
	$DAEMON start
}

do_stop()
{
	$DAEMON stop
}

case "$1" in
  start)
	[ "$VERBOSE" != no ] && log_daemon_msg "Starting $DESC " "$NAME"
	do_start
	case "$?" in
		0|1) [ "$VERBOSE" != no ] && log_end_msg 0 ;;
		2) [ "$VERBOSE" != no ] && log_end_msg 1 ;;
	esac
	;;
  stop)
	[ "$VERBOSE" != no ] && log_daemon_msg "Stopping $DESC" "$NAME"
	do_stop
	case "$?" in
		0|1) [ "$VERBOSE" != no ] && log_end_msg 0 ;;
		2) [ "$VERBOSE" != no ] && log_end_msg 1 ;;
	esac
	;;
  status)
	status_of_proc "$DAEMON" "$NAME" && exit 0 || exit $?
	;;
  restart|force-reload)
	log_daemon_msg "Restarting $DESC" "$NAME"
	do_stop
	case "$?" in
	  0|1)
		do_start
		case "$?" in
			0) log_end_msg 0 ;;
			1) log_end_msg 1 ;;
			*) log_end_msg 1 ;;
		esac
		;;
	  *)
		log_end_msg 1
		;;
	esac
	;;
  *)
	echo "Usage: $SCRIPTNAME {start|stop|status|restart|force-reload}" >&2
	exit 3
	;;
esac

:
