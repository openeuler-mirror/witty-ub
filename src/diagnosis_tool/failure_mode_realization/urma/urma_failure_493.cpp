#include "urma_failure_493.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure493> g_urma("urma_493");

bool UrmaFailure493::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'bondp_jfs_get_args_list' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid param jfc'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure493::GetName() const
{
    return "bondp_jfs_get_args_list 校验 JFS 无效导致获取流程拒绝继续执行";
}

std::string UrmaFailure493::GetRootCauseDesc() const
{
    return "bondp_jfs_get_args_list 在执行获取前发现调用方传入的 JFS "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure493::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure493::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure493::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid param jfc";
}

std::string UrmaFailure493::GetId() const
{
    return "urma_493";
}

} // namespace diag
