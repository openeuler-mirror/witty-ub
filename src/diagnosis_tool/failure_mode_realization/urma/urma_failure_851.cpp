#include "urma_failure_851.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure851> g_urma("urma_851");

bool UrmaFailure851::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'bondp_handle_cr_no_store' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Invalid cr error status:')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure851::GetName() const
{
    return "bondp_handle_cr_no_store 校验 WR 无效导致处理流程拒绝继续执行";
}

std::string UrmaFailure851::GetRootCauseDesc() const
{
    return "bondp_handle_cr_no_store 在执行处理前发现调用方传入的 WR "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure851::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure851::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure851::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid cr error status";
}

std::string UrmaFailure851::GetId() const
{
    return "urma_851";
}

} // namespace diag
