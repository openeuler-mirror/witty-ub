#include "urma_failure_393.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure393> g_urma("urma_393");

bool UrmaFailure393::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_set_jfs_opt' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'invalid opt id or opt len')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure393::GetName() const
{
    return "urma_set_jfs_opt 校验 JFS 无效导致设置流程拒绝继续执行";
}

std::string UrmaFailure393::GetRootCauseDesc() const
{
    return "urma_set_jfs_opt 在执行设置前发现调用方传入的 JFS 不满足当前操作要求，通常是对象为空、状态不匹配或与 "
           "provider 能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure393::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure393::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure393::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：invalid opt id or opt len";
}

std::string UrmaFailure393::GetId() const
{
    return "urma_393";
}

} // namespace diag
