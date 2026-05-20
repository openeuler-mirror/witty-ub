#include "urma_failure_003.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure003> g_urma("urma_003");

bool UrmaFailure003::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_register_log_func' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure003::GetName() const
{
    return "urma_register_log_func 校验 URMA 对象 无效导致注册流程拒绝继续执行";
}

std::string UrmaFailure003::GetRootCauseDesc() const
{
    return "urma_register_log_func 在执行注册前发现调用方传入的 URMA 对象 "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure003::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure003::GetFixSuggDesc() const
{
    return "当前不会触发失败";
}

std::string UrmaFailure003::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid parameter";
}

std::string UrmaFailure003::GetId() const
{
    return "urma_003";
}

} // namespace diag
