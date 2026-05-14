#include "urma_failure_482.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure482> g_urma("urma_482");

bool UrmaFailure482::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_create_context' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Invalid parameter with err dev or ops')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure482::GetName() const
{
    return "urma_create_context 校验 context 无效导致创建流程拒绝继续执行";
}

std::string UrmaFailure482::GetRootCauseDesc() const
{
    return "urma_create_context 在执行创建前发现调用方传入的 context "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure482::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure482::GetFixSuggDesc() const
{
    return "当前不会触发";
}

std::string UrmaFailure482::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid parameter with err dev or ops";
}

std::string UrmaFailure482::GetId() const
{
    return "urma_482";
}

} // namespace diag
