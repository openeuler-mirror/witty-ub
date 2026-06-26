#include "urma_failure_238.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure238> g_urma("urma_238");

bool UrmaFailure238::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("update_mapping_hash_table") != std::string::npos &&
           message.find("Failed to add port eid to mapping hash table") != std::string::npos;
}

std::string UrmaFailure238::GetName() const
{
    return "updateupdate、mapping、HASH执行失败导致updateupdate、mapping、HASH失败";
}

std::string UrmaFailure238::GetRootCauseDesc() const
{
    return "update_mapping_hash_"
           "table执行updateupdate、mapping、HASH时依赖的updateupdate、mapping、HASH步骤返回错误，当前URMA操作无法继续完"
           "成"
           "。";
}

RootCause UrmaFailure238::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure238::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure238::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：update_mapping_hash_table，Failed to add port eid to mapping hash "
           "table。";
}

std::string UrmaFailure238::GetId() const
{
    return "urma_238";
}
} // namespace diag
