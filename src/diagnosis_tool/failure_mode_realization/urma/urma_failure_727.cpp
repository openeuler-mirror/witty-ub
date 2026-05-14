#include "urma_failure_727.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure727> g_urma("urma_727");

bool UrmaFailure727::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_cmd_delete_jfs_batch' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Invalid parameter')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure727::GetName() const
{
    return "urma_cmd_delete_jfs_batch 校验 JFS 无效导致删除流程拒绝继续执行";
}

std::string UrmaFailure727::GetRootCauseDesc() const
{
    return "urma_cmd_delete_jfs_batch 在执行删除前发现调用方传入的 JFS "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure727::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure727::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure727::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid parameter";
}

std::string UrmaFailure727::GetId() const
{
    return "urma_727";
}

} // namespace diag
