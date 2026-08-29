// SPDX-License-Identifier: Apache-2.0

#include <KIdleTime>
#include <QCommandLineOption>
#include <QCommandLineParser>
#include <QGuiApplication>
#include <QObject>

#include <iostream>
#include <limits>

namespace
{
void emitEvent(const char *event)
{
    std::cout << "CWS_EVENT " << event << '\n' << std::flush;
}

int parseSeconds(const QCommandLineParser &parser, const QCommandLineOption &option)
{
    bool ok = false;
    const qlonglong seconds = parser.value(option).toLongLong(&ok);
    constexpr qlonglong maxSeconds = std::numeric_limits<int>::max() / 1000;
    if (!ok || seconds < 1 || seconds > maxSeconds) {
        return -1;
    }
    return static_cast<int>(seconds * 1000);
}
}

int main(int argc, char **argv)
{
    QGuiApplication application(argc, argv);
    QGuiApplication::setApplicationName(QStringLiteral("cachy-workstation-idle-agent"));
    QGuiApplication::setQuitOnLastWindowClosed(false);

    QCommandLineParser parser;
    parser.setApplicationDescription(QStringLiteral("KDE input-idle event agent"));
    parser.addHelpOption();
    const QCommandLineOption lockOption(QStringLiteral("lock-seconds"),
                                        QStringLiteral("Idle seconds before locking"),
                                        QStringLiteral("seconds"));
    const QCommandLineOption shutdownOption(QStringLiteral("shutdown-seconds"),
                                            QStringLiteral("Idle seconds before poweroff"),
                                            QStringLiteral("seconds"));
    parser.addOption(lockOption);
    parser.addOption(shutdownOption);
    parser.process(application);

    const int lockMilliseconds = parseSeconds(parser, lockOption);
    const int shutdownMilliseconds = parseSeconds(parser, shutdownOption);
    if (lockMilliseconds < 0 || shutdownMilliseconds <= lockMilliseconds) {
        std::cerr << "Invalid idle policy intervals" << std::endl;
        return 2;
    }

    KIdleTime *idle = KIdleTime::instance();
    bool lockEmitted = false;
    bool poweroffEmitted = false;

    QObject::connect(idle,
                     qOverload<int, int>(&KIdleTime::timeoutReached),
                     &application,
                     [&](int, int timeout) {
                         if (timeout == shutdownMilliseconds && !poweroffEmitted) {
                             poweroffEmitted = true;
                             emitEvent("POWER_OFF");
                         } else if (timeout == lockMilliseconds && !lockEmitted) {
                             lockEmitted = true;
                             idle->catchNextResumeEvent();
                             emitEvent("LOCK");
                         }
                     });
    QObject::connect(idle, &KIdleTime::resumingFromIdle, &application, [&]() {
        lockEmitted = false;
        poweroffEmitted = false;
        emitEvent("RESUMED");
    });

    idle->removeAllIdleTimeouts();
    idle->addIdleTimeout(lockMilliseconds);
    idle->addIdleTimeout(shutdownMilliseconds);

    const int initialIdle = idle->idleTime();
    std::cout << "CWS_EVENT READY idle_ms=" << initialIdle << " lock_ms=" << lockMilliseconds
              << " shutdown_ms=" << shutdownMilliseconds << '\n'
              << std::flush;
    if (initialIdle >= shutdownMilliseconds) {
        poweroffEmitted = true;
        emitEvent("POWER_OFF");
    } else if (initialIdle >= lockMilliseconds) {
        lockEmitted = true;
        idle->catchNextResumeEvent();
        emitEvent("LOCK");
    }

    return application.exec();
}
