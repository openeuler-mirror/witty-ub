#include "urma_failure_504.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure504> g_urma("urma_504");

bool UrmaFailure504::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_cmd_query_jfs' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Invalid parameter')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure504::GetName() const
{
    return "urma_cmd_query_jfs 校验 context 无效导致查询流程拒绝继续执行";
}

std::string UrmaFailure504::GetRootCauseDesc() const
{
    return "urma_cmd_query_jfs 在执行查询前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 "
           "provider 能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure504::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure504::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure504::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid parameter";
}

std::string UrmaFailure504::GetId() const
{
    return "urma_504";
}

} // namespace diag
