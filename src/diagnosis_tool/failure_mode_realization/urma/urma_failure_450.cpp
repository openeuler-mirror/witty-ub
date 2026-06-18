#include "urma_failure_450.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure450> g_urma("urma_450");

bool UrmaFailure450::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_delete_jfc") != std::string::npos &&
           message.find("jfc is deactived, can not delete.") != std::string::npos;
}

std::string UrmaFailure450::GetName() const
{
    return "JFC状态不满足要求导致删除JFC失败";
}

std::string UrmaFailure450::GetRootCauseDesc() const
{
    return "urma_delete_jfc执行删除JFC时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure450::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure450::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure450::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jfc，jfc is deactived, can not delete.。";
}

std::string UrmaFailure450::GetId() const
{
    return "urma_450";
}
} // namespace diag
