#include "urma_failure_576.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure576> g_urma("urma_576");

bool UrmaFailure576::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_delete_jfr") != std::string::npos &&
           message.find("jfr is deactived, can not delete.") != std::string::npos;
}

std::string UrmaFailure576::GetName() const
{
    return "JFR状态不满足要求导致删除JFR失败";
}

std::string UrmaFailure576::GetRootCauseDesc() const
{
    return "urma_delete_jfr执行删除JFR时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure576::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure576::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure576::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jfr，jfr is deactived, can not delete.。";
}

std::string UrmaFailure576::GetId() const
{
    return "urma_576";
}
} // namespace diag
