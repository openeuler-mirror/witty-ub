#include "urma_failure_721.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure721> g_urma("urma_721");

bool UrmaFailure721::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'delete_copied_jfs_wr' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Invalid jfs wr to delete')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure721::GetName() const
{
    return "delete_copied_jfs_wr 校验 JFS 无效导致删除流程拒绝继续执行";
}

std::string UrmaFailure721::GetRootCauseDesc() const
{
    return "delete_copied_jfs_wr 在执行删除前发现调用方传入的 JFS 不满足当前操作要求，通常是对象为空、状态不匹配或与 "
           "provider 能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure721::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure721::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure721::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid jfs wr to delete";
}

std::string UrmaFailure721::GetId() const
{
    return "urma_721";
}

} // namespace diag
