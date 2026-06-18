#include "urma_failure_563.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure563> g_urma("urma_563");

bool UrmaFailure563::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_delete_jfs") != std::string::npos &&
           message.find("jfs is deactived, can not delete.") != std::string::npos;
}

std::string UrmaFailure563::GetName() const
{
    return "JFS状态不满足要求导致删除JFS失败";
}

std::string UrmaFailure563::GetRootCauseDesc() const
{
    return "urma_delete_jfs执行删除JFS时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure563::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure563::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure563::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jfs，jfs is deactived, can not delete.。";
}

std::string UrmaFailure563::GetId() const
{
    return "urma_563";
}
} // namespace diag
