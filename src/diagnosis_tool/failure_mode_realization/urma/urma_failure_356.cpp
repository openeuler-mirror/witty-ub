#include "urma_failure_356.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure356> g_urma("urma_356");

bool UrmaFailure356::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'update_mapping_hash_table' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F "
        "'Failed to create eid_mapping_hash_table'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure356::GetName() const
{
    return "EID创建时下层资源准备失败";
}

std::string UrmaFailure356::GetRootCauseDesc() const
{
    return "函数负责创建EID，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure356::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure356::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure356::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：update_mapping_hash_table，Failed to create eid_mapping_hash_table。";
}

std::string UrmaFailure356::GetId() const
{
    return "urma_356";
}

} // namespace diag
