#include "urma_failure_070.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure070> g_urma("urma_070");

bool UrmaFailure070::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_cmd_set_jetty_opt' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'jetty->jetty_cfg.jfs_cfg.jfc is not exist'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure070::GetName() const
{
    return "urma_cmd_set_jetty_opt URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断";
}

std::string UrmaFailure070::GetRootCauseDesc() const
{
    return "urma_cmd_set_jetty_opt 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl "
           "返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 Jetty 状态。";
}

RootCause UrmaFailure070::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure070::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure070::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：jetty->jetty_cfg.jfs_cfg.jfc is not exist";
}

std::string UrmaFailure070::GetId() const
{
    return "urma_070";
}

} // namespace diag
