#include "urma_failure_346.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure346> g_urma("urma_346");

bool UrmaFailure346::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_cmd_create_jetty' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'failed to init create jetty cmd')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure346::GetName() const
{
    return "urma_cmd_create_jetty URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断";
}

std::string UrmaFailure346::GetRootCauseDesc() const
{
    return "urma_cmd_create_jetty 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl "
           "返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 Jetty 状态。";
}

RootCause UrmaFailure346::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure346::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure346::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：failed to init create jetty cmd";
}

std::string UrmaFailure346::GetId() const
{
    return "urma_346";
}

} // namespace diag
