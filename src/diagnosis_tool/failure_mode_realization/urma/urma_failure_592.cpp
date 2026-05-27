#include "urma_failure_592.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure592> g_urma("urma_592");

bool UrmaFailure592::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_delete_jfc' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to delete jfc[' | grep -F '], still in use. use_cnt:' | grep -F 'u'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure592::GetName() const
{
    return "JFC清理阶段下层释放操作失败";
}

std::string UrmaFailure592::GetRootCauseDesc() const
{
    return "函数负责释放或撤销JFC相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure592::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure592::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure592::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_delete_jfc，Failed to delete jfc[，], still in use. use_cnt:，u";
}

std::string UrmaFailure592::GetId() const
{
    return "urma_592";
}

} // namespace diag
