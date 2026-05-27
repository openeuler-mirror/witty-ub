#include "urma_failure_598.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure598> g_urma("urma_598");

bool UrmaFailure598::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_delete_pjfc' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to delete pjfc' | grep -F ', ret:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure598::GetName() const
{
    return "物理 JFC清理阶段下层释放操作失败";
}

std::string UrmaFailure598::GetRootCauseDesc() const
{
    return "函数负责释放或撤销物理 JFC相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure598::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure598::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure598::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_delete_pjfc，Failed to delete pjfc，, ret:。";
}

std::string UrmaFailure598::GetId() const
{
    return "urma_598";
}

} // namespace diag
