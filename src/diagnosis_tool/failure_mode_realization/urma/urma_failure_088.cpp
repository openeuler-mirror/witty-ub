#include "urma_failure_088.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure088> g_urma("urma_088");

bool UrmaFailure088::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_cmd_set_tp_attr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid tp_attr bytes'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure088::GetName() const
{
    return "urma_cmd_set_tp_attr 校验 TP 无效导致设置流程拒绝继续执行";
}

std::string UrmaFailure088::GetRootCauseDesc() const
{
    return "urma_cmd_set_tp_attr 在执行设置前发现调用方传入的 TP 不满足当前操作要求，通常是对象为空、状态不匹配或与 "
           "provider 能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure088::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure088::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure088::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid tp_attr bytes";
}

std::string UrmaFailure088::GetId() const
{
    return "urma_088";
}

} // namespace diag
