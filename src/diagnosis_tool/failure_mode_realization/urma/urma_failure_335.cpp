#include "urma_failure_335.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure335> g_urma("urma_335");

bool UrmaFailure335::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_cmd_set_jfc_opt' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'ioctl failed in urma_cmd_set_jfc_opt, ret:, errno')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure335::GetName() const
{
    return "urma_cmd_set_jfc_opt URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断";
}

std::string UrmaFailure335::GetRootCauseDesc() const
{
    return "urma_cmd_set_jfc_opt 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl "
           "返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 JFC 状态。";
}

RootCause UrmaFailure335::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure335::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure335::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：ioctl failed in urma_cmd_set_jfc_opt, ret:, errno";
}

std::string UrmaFailure335::GetId() const
{
    return "urma_335";
}

} // namespace diag
