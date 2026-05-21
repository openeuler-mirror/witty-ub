#include "urma_failure_714.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure714> g_urma("urma_714");

bool UrmaFailure714::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'bondp_delete_comp' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid param'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure714::GetName() const
{
    return "bondp_delete_comp 校验 URMA 对象 无效导致删除流程拒绝继续执行";
}

std::string UrmaFailure714::GetRootCauseDesc() const
{
    return "bondp_delete_comp 在执行删除前发现调用方传入的 URMA 对象 "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure714::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure714::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure714::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid param";
}

std::string UrmaFailure714::GetId() const
{
    return "urma_714";
}

} // namespace diag
