#include "urma_failure_583.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure583> g_urma("urma_583");

bool UrmaFailure583::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_deactive_jfr") != std::string::npos &&
           message.find("jfr state is wrong in deactive_jfr.") != std::string::npos;
}

std::string UrmaFailure583::GetName() const
{
    return "JFR状态不满足要求导致去激活JFR失败";
}

std::string UrmaFailure583::GetRootCauseDesc() const
{
    return "urma_deactive_jfr执行去激活JFR时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure583::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure583::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure583::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_deactive_jfr，jfr state is wrong in deactive_jfr.。";
}

std::string UrmaFailure583::GetId() const
{
    return "urma_583";
}
} // namespace diag
