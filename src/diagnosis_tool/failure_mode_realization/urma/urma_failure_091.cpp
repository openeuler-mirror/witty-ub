#include "urma_failure_091.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure091> g_urma("urma_091");

bool UrmaFailure091::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_cmd_get_tp_attr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid tp_attr bytes'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure091::GetName() const
{
    return "urma_cmd_get_tp_attr 校验 TP 无效导致获取流程拒绝继续执行";
}

std::string UrmaFailure091::GetRootCauseDesc() const
{
    return "urma_cmd_get_tp_attr 在执行获取前发现调用方传入的 TP 不满足当前操作要求，通常是对象为空、状态不匹配或与 "
           "provider 能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure091::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure091::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure091::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid tp_attr bytes";
}

std::string UrmaFailure091::GetId() const
{
    return "urma_091";
}

} // namespace diag
