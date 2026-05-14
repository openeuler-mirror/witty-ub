#include "urma_failure_426.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure426> g_urma("urma_426");

bool UrmaFailure426::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_create_jetty_check_jfc' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Invalid parameter, jfr cfg is null or jfc is NULL with non shared jfr flag')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure426::GetName() const
{
    return "urma_create_jetty_check_jfc 校验 Jetty 无效导致创建流程拒绝继续执行";
}

std::string UrmaFailure426::GetRootCauseDesc() const
{
    return "urma_create_jetty_check_jfc 在执行创建前发现调用方传入的 Jetty "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure426::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure426::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure426::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid parameter, jfr cfg is null or jfc is NULL with non shared jfr "
           "flag";
}

std::string UrmaFailure426::GetId() const
{
    return "urma_426";
}

} // namespace diag
