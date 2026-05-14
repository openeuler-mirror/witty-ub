#include "urma_failure_421.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure421> g_urma("urma_421");

bool UrmaFailure421::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_create_jetty_check_trans_mode' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'jfr cfg is null or trans_mode or order_type invalid with non shared jfr flag')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure421::GetName() const
{
    return "urma_create_jetty_check_trans_mode 校验 Jetty 无效导致创建流程拒绝继续执行";
}

std::string UrmaFailure421::GetRootCauseDesc() const
{
    return "urma_create_jetty_check_trans_mode 在执行创建前发现调用方传入的 Jetty "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure421::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure421::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure421::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：jfr cfg is null or trans_mode or order_type invalid with non shared jfr "
           "flag";
}

std::string UrmaFailure421::GetId() const
{
    return "urma_421";
}

} // namespace diag
