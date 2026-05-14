#include "urma_failure_723.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure723> g_urma("urma_723");

bool UrmaFailure723::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'delete_copied_jfr_wr' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Invalid jfr wr to delete')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure723::GetName() const
{
    return "delete_copied_jfr_wr 校验 JFR 无效导致删除流程拒绝继续执行";
}

std::string UrmaFailure723::GetRootCauseDesc() const
{
    return "delete_copied_jfr_wr 在执行删除前发现调用方传入的 JFR 不满足当前操作要求，通常是对象为空、状态不匹配或与 "
           "provider 能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure723::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure723::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure723::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid jfr wr to delete";
}

std::string UrmaFailure723::GetId() const
{
    return "urma_723";
}

} // namespace diag
