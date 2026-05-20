#include "urma_failure_004.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure004> g_urma("urma_004");

bool UrmaFailure004::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_register_provider_ops' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure004::GetName() const
{
    return "urma_register_provider_ops 校验 provider 无效导致注册流程拒绝继续执行";
}

std::string UrmaFailure004::GetRootCauseDesc() const
{
    return "urma_register_provider_ops 在执行注册前发现调用方传入的 provider "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure004::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure004::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure004::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid parameter";
}

std::string UrmaFailure004::GetId() const
{
    return "urma_004";
}

} // namespace diag
