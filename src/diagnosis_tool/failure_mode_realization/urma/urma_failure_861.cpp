#include "urma_failure_861.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure861> g_urma("urma_861");

bool UrmaFailure861::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'update_mapping_hash_table' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to add agg eid to mapping hash table'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure861::GetName() const
{
    return "update_mapping_hash_table 更新 设备 映射结构失败导致资源索引不可用";
}

std::string UrmaFailure861::GetRootCauseDesc() const
{
    return "update_mapping_hash_table 需要维护 设备 "
           "到物理资源或虚拟资源的映射关系，但哈希表创建、插入、删除或查找失败，后续无法通过标识定位正确资源。";
}

RootCause UrmaFailure861::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure861::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure861::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to add agg eid to mapping hash table";
}

std::string UrmaFailure861::GetId() const
{
    return "urma_861";
}

} // namespace diag
