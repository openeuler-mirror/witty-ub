#include "urma_failure_467.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure467> g_urma("urma_467");

bool UrmaFailure467::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_free_token_id' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure467::GetName() const
{
    return "urma_free_token_id 校验 token_id 无效导致释放流程拒绝继续执行";
}

std::string UrmaFailure467::GetRootCauseDesc() const
{
    return "urma_free_token_id 在执行释放前发现调用方传入的 token_id "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure467::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure467::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure467::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid parameter";
}

std::string UrmaFailure467::GetId() const
{
    return "urma_467";
}

} // namespace diag
