#include "urma_failure_383.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure383> g_urma("urma_383");

bool UrmaFailure383::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_delete_jfs_batch' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Invalid parameter')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure383::GetName() const
{
    return "urma_delete_jfs_batch 校验 JFS 无效导致删除流程拒绝继续执行";
}

std::string UrmaFailure383::GetRootCauseDesc() const
{
    return "urma_delete_jfs_batch 在执行删除前发现调用方传入的 JFS 不满足当前操作要求，通常是对象为空、状态不匹配或与 "
           "provider 能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure383::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure383::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure383::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid parameter";
}

std::string UrmaFailure383::GetId() const
{
    return "urma_383";
}

} // namespace diag
