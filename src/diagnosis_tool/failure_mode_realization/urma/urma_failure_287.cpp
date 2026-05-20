#include "urma_failure_287.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure287> g_urma("urma_287");

bool UrmaFailure287::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'create_topo_map' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to create eid_mapping_hash_table'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure287::GetName() const
{
    return "create_topo_map 更新 EID 映射结构失败导致资源索引不可用";
}

std::string UrmaFailure287::GetRootCauseDesc() const
{
    return "create_topo_map 需要维护 EID "
           "到物理资源或虚拟资源的映射关系，但哈希表创建、插入、删除或查找失败，后续无法通过标识定位正确资源。";
}

RootCause UrmaFailure287::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure287::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure287::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to create eid_mapping_hash_table";
}

std::string UrmaFailure287::GetId() const
{
    return "urma_287";
}

} // namespace diag
