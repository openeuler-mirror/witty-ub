#include "urma_failure_034.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure034> g_urma("urma_034");

bool UrmaFailure034::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_cmd_get_jfs_opt' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'output length too large, out.len=, buf.len=')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure034::GetName() const
{
    return "urma_cmd_get_jfs_opt URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断";
}

std::string UrmaFailure034::GetRootCauseDesc() const
{
    return "urma_cmd_get_jfs_opt 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl "
           "返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 JFS 状态。";
}

RootCause UrmaFailure034::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure034::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure034::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：output length too large, out.len=, buf.len=";
}

std::string UrmaFailure034::GetId() const
{
    return "urma_034";
}

} // namespace diag
