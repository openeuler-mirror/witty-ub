#include "urma_failure_566.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure566> g_urma("urma_566");

bool UrmaFailure566::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_delete_jfs_batch") != std::string::npos &&
           message.find("Invalid parameter, index:") != std::string::npos &&
           message.find("jfs in the array is NULL.") != std::string::npos;
}

std::string UrmaFailure566::GetName() const
{
    return "urma_ctx_arr无效导致删除JFS失败";
}

std::string UrmaFailure566::GetRootCauseDesc() const
{
    return "urma_delete_jfs_batch用于删除JFS，调用方传入的urma_ctx_arr不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure566::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure566::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure566::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jfs_batch，Invalid parameter, index:，jfs in the array is "
           "NULL.。";
}

std::string UrmaFailure566::GetId() const
{
    return "urma_566";
}
} // namespace diag
