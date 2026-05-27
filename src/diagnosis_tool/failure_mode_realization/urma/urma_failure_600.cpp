#include "urma_failure_600.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure600> g_urma("urma_600");

bool UrmaFailure600::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_delete_jfr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to delete jfr[' | grep -F '], still in use. use_cnt:' | grep -F 'u'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure600::GetName() const
{
    return "JFR清理阶段下层释放操作失败";
}

std::string UrmaFailure600::GetRootCauseDesc() const
{
    return "函数负责释放或撤销JFR相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure600::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure600::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure600::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_delete_jfr，Failed to delete jfr[，], still in use. use_cnt:，u";
}

std::string UrmaFailure600::GetId() const
{
    return "urma_600";
}

} // namespace diag
