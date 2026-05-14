#include "urma_failure_869.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure869> g_urma("urma_869");

bool UrmaFailure869::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'deepcopy_jfs_wr_inner' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Invalid jfs wr to deepcopy')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure869::GetName() const
{
    return "deepcopy_jfs_wr_inner 校验 JFS 无效导致复制流程拒绝继续执行";
}

std::string UrmaFailure869::GetRootCauseDesc() const
{
    return "deepcopy_jfs_wr_inner 在执行复制前发现调用方传入的 JFS 不满足当前操作要求，通常是对象为空、状态不匹配或与 "
           "provider 能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure869::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure869::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure869::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid jfs wr to deepcopy";
}

std::string UrmaFailure869::GetId() const
{
    return "urma_869";
}

} // namespace diag
