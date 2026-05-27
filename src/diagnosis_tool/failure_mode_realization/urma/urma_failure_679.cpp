#include "urma_failure_679.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure679> g_urma("urma_679");

bool UrmaFailure679::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_jfce' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F '[DRV_ERR]Failed to delete jfce, ret:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure679::GetName() const
{
    return "JFCE清理阶段下层释放操作失败";
}

std::string UrmaFailure679::GetRootCauseDesc() const
{
    return "函数负责释放或撤销JFCE相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure679::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure679::GetFixSuggDesc() const
{
    return "当前不会触发";
}

std::string UrmaFailure679::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_delete_jfce，[DRV_ERR]Failed to delete jfce, ret:";
}

std::string UrmaFailure679::GetId() const
{
    return "urma_679";
}

} // namespace diag
