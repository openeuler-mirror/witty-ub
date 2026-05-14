#include "urma_failure_288.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure288> g_urma("urma_288");

bool UrmaFailure288::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'deepcopy_sge' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Invalid sge pointer, dst or src is NULL')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure288::GetName() const
{
    return "deepcopy_sge 校验 SGE 无效导致复制流程拒绝继续执行";
}

std::string UrmaFailure288::GetRootCauseDesc() const
{
    return "deepcopy_sge 在执行复制前发现调用方传入的 SGE 不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure288::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure288::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure288::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid sge pointer, dst or src is NULL";
}

std::string UrmaFailure288::GetId() const
{
    return "urma_288";
}

} // namespace diag
