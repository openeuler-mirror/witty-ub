#include "urma_failure_109.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure109> g_urma("urma_109");

bool UrmaFailure109::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_relink_primary_import' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F "
        "'Failed to import recreated primary ptjetty, local_idx:' | grep -F 'target_idx:' | grep -F 'pjetty_id:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure109::GetName() const
{
    return "物理 Jetty导入时下层资源准备失败";
}

std::string UrmaFailure109::GetRootCauseDesc() const
{
    return "函数负责导入物理 Jetty，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure109::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure109::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure109::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_relink_primary_import，Failed to import recreated primary "
           "ptjetty, local_idx:，target_idx:，pjetty_id:。";
}

std::string UrmaFailure109::GetId() const
{
    return "urma_109";
}

} // namespace diag
