#include "urma_failure_676.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure676> g_urma("urma_676");

bool UrmaFailure676::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_jfr' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'jfr is deactived, can not delete.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure676::GetName() const
{
    return "JFR清理阶段下层释放操作失败";
}

std::string UrmaFailure676::GetRootCauseDesc() const
{
    return "函数负责释放或撤销JFR相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure676::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure676::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure676::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jfr，jfr is deactived, can not delete.。";
}

std::string UrmaFailure676::GetId() const
{
    return "urma_676";
}

} // namespace diag
