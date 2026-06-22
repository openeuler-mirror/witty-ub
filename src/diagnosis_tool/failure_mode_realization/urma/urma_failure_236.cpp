#include "urma_failure_236.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure236> g_urma("urma_236");

bool UrmaFailure236::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("update_mapping_hash_table") != std::string::npos &&
           message.find("Failed to add agg eid to mapping hash table") != std::string::npos;
}

std::string UrmaFailure236::GetName() const
{
    return "updateupdate、mapping、HASH执行失败导致updateupdate、mapping、HASH失败";
}

std::string UrmaFailure236::GetRootCauseDesc() const
{
    return "update_mapping_hash_"
           "table执行updateupdate、mapping、HASH时依赖的updateupdate、mapping、HASH步骤返回错误，当前URMA操作无法继续完"
           "成"
           "。";
}

RootCause UrmaFailure236::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure236::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure236::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：update_mapping_hash_table，Failed to add agg eid to mapping hash "
           "table。";
}

std::string UrmaFailure236::GetId() const
{
    return "urma_236";
}
} // namespace diag
