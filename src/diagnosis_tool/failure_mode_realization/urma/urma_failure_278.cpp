#include "urma_failure_278.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure278> g_urma("urma_278");

bool UrmaFailure278::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'bdp_queue_push_tail' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Failed to enqueue with invalid node_num: , max_node')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure278::GetName() const
{
    return "bdp_queue_push_tail 校验 URMA 对象 无效导致处理流程拒绝继续执行";
}

std::string UrmaFailure278::GetRootCauseDesc() const
{
    return "bdp_queue_push_tail 在执行处理前发现调用方传入的 URMA 对象 "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure278::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure278::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure278::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to enqueue with invalid node_num: , max_node";
}

std::string UrmaFailure278::GetId() const
{
    return "urma_278";
}

} // namespace diag
