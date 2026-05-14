#include "urma_failure_092.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure092> g_urma("urma_092");

bool UrmaFailure092::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_cmd_get_tp_attr' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Failed in ioctl get_tp_attr, ret')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure092::GetName() const
{
    return "urma_cmd_get_tp_attr URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断";
}

std::string UrmaFailure092::GetRootCauseDesc() const
{
    return "urma_cmd_get_tp_attr 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl "
           "返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 TP 状态。";
}

RootCause UrmaFailure092::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure092::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure092::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed in ioctl get_tp_attr, ret";
}

std::string UrmaFailure092::GetId() const
{
    return "urma_092";
}

} // namespace diag
