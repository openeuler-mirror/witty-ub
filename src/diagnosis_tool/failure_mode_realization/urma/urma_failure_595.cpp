#include "urma_failure_595.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure595> g_urma("urma_595");

bool UrmaFailure595::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_delete_jfce' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Failed to "
        "delete jfce[' | grep -F '], still in use. use_cnt:' | grep -F 'u'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure595::GetName() const
{
    return "JFCE清理阶段下层释放操作失败";
}

std::string UrmaFailure595::GetRootCauseDesc() const
{
    return "函数负责释放或撤销JFCE相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure595::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure595::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure595::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_delete_jfce，Failed to delete jfce[，], still in use. "
           "use_cnt:，u。";
}

std::string UrmaFailure595::GetId() const
{
    return "urma_595";
}

} // namespace diag
