#include "urma_failure_420.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure420> g_urma("urma_420");

bool UrmaFailure420::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_create_jetty_check_trans_mode' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Invalid parameter, trans_mode:' | grep -F ', order_type:')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure420::GetName() const
{
    return "urma_create_jetty_check_trans_mode 校验 Jetty 无效导致创建流程拒绝继续执行";
}

std::string UrmaFailure420::GetRootCauseDesc() const
{
    return "urma_create_jetty_check_trans_mode 在执行创建前发现调用方传入的 Jetty "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure420::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure420::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure420::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid parameter, trans_mode: , order_type";
}

std::string UrmaFailure420::GetId() const
{
    return "urma_420";
}

} // namespace diag
