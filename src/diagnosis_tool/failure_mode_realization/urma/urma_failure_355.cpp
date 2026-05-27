#include "urma_failure_355.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure355> g_urma("urma_355");

bool UrmaFailure355::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'update_mapping_hash_table' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Failed to alloc topo_map'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure355::GetName() const
{
    return "URMA资源相关临时结构或命令参数分配失败";
}

std::string UrmaFailure355::GetRootCauseDesc() const
{
    return "函数在分配URMA资源前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。";
}

RootCause UrmaFailure355::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure355::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure355::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：update_mapping_hash_table，Failed to alloc topo_map。";
}

std::string UrmaFailure355::GetId() const
{
    return "urma_355";
}

} // namespace diag
