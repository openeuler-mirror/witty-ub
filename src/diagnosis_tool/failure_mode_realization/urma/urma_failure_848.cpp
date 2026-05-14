#include "urma_failure_848.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure848> g_urma("urma_848");

bool UrmaFailure848::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'BDP_V_CONN_HASH_BASIS' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Invalid param')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure848::GetName() const
{
    return "BDP_V_CONN_HASH_BASIS 校验 Jetty 无效导致处理流程拒绝继续执行";
}

std::string UrmaFailure848::GetRootCauseDesc() const
{
    return "BDP_V_CONN_HASH_BASIS 在执行处理前发现调用方传入的 Jetty "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure848::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure848::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure848::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid param";
}

std::string UrmaFailure848::GetId() const
{
    return "urma_848";
}

} // namespace diag
